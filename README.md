# Sail – Serverless RAG Stack

Sail is a fullstack Retrieval Augmented Generation (RAG) project for students to get answers only based on the uploaded material. It combines AWS serverless primitives (API Gateway, Lambda, DynamoDB, S3, Secrets Manager, Lambda Layers) with a lightweight Next.js frontend. Users create chat sessions, upload plain text documents, trigger ingestion to build a FAISS index, and query the index with OpenAI models.


## Architecture & Workflow Snapshot

1. **Create session** – `POST /sessions` persists a manifest under `s3://rag-docs-<project>/default/sessions/{sessionId}/manifest.json`.
2. **Upload artifacts** – `POST /upload-url` returns an S3 presigned URL. Files land in `.../uploads/`.
3. **Ingest** – `POST /ingest` downloads `.txt` uploads, chunks text, embeds via OpenAI, builds FAISS, and writes `index/faiss.index`, `index/meta.json`, and `index/stats.json` under the session prefix.
4. **Query** – `POST /query` loads the cached FAISS index, retrieves top chunks, calls OpenAI Chat, returns the answer plus cited chunks, and appends the conversation to DynamoDB/S3.
5. **Get messages** – `GET /sessions/{sessionId}/messages` pulls the session history for the frontend sidebar.

Required services: AWS account with Terraform access, S3, API Gateway HTTP API, Lambda (Python 3.11, x86_64), Secrets Manager (OpenAI API key), DynamoDB (chat history), and FAISS compatible Lambda Layers.


## Repository Layout

```
backend/            # Lambda sources (one folder per function)
frontend/           # Next.js 16 client served locally or via any static host
layers/             # Lambda layer contents (code + dependencies)
terraform/          # IaC for all AWS resources (bucket, lambdas, API, etc.)
plan.md             # Architectural design notes and backlog
```

## Backend (`backend/`)

### Lambda Functions (`backend/lambdas/*`)

| Lambda | Description | Key Environment Variables |
| --- | --- | --- |
| `create_session` | Generates or accepts a `sessionId`, writes a manifest JSON into S3, returns metadata to the client. | `BUCKET`, `NAMESPACE` |
| `get_upload_url` | Issues an S3 presigned PUT URL so the browser can upload directly to `sessions/{sessionId}/uploads/`. | `BUCKET`, `NAMESPACE` |
| `ingest` | Lists `.txt` uploads, downloads to `/tmp`, chunks with `backend.shared.chunk_text`, embeds via OpenAI, builds & uploads FAISS index and metadata. | `BUCKET`, `NAMESPACE`, `OPENAI_SECRET_ARN`, `EMBED_MODEL` |
| `query` | Verifies index artifacts exist, lazily caches FAISS+metadata per session using S3 ETags, embeds the incoming question, searches the index, composes OpenAI chat messages, saves conversation turns, and returns answers + cited chunks. | `BUCKET`, `NAMESPACE`, `OPENAI_SECRET_ARN`, `CHAT_MODEL`, `MESSAGES_TABLE` |
| `get_messages` | REST endpoint to pull the full conversation history for a session (reads from DynamoDB via shared utilities). | `BUCKET`, `NAMESPACE`, `MESSAGES_TABLE` |

Implementation notes:

- All handlers rely on shared utilities via the Lambda code layer, so imports such as `from backend.shared import ...` work consistently both locally and in Lambda.
- `ingest` currently accepts plain text uploads (`.txt`). Extend `extract_pdf` usage for PDFs if needed.
- `query` caches FAISS indices in the `_cache` dict keyed by session ID and validates freshness via `get_etag`. Messages are saved twice: raw JSON under S3 and structured records in DynamoDB.

### Shared Modules (`layers/code/python/backend/shared/`)

| Module | Purpose |
| --- | --- |
| `s3_utils.py` | Centralized S3 client, presigned PUT generation, download/upload helpers, object existence checks, and ETag fetchers. |
| `openai_utils.py` | Retrieves the OpenAI API key from Secrets Manager (`OPENAI_SECRET_ARN`) and exposes `embed_texts` + `chat` helpers with overridable model names via env vars. |
| `chunking.py` | GPT-4 token counting, sentence-aware chunker with overlap, plus extractors for `.pdf` and `.txt`. |
| `faiss_utils.py` | Creates/searches FAISS `IndexFlatIP`, normalizes vectors, serializes metadata, merges indexes when needed. |
| `message_utils.py` | Persists conversation history either in S3 (`messages.json`) or DynamoDB (default), converts chunks to Dynamo-safe formats, builds OpenAI message arrays with the system prompt. |
| `dynamodb_utils.py` | Cached DynamoDB resource and table helpers honoring `AWS_REGION`/`AWS-REGION`. |

These modules are surfaced via `backend/shared/__init__.py`, so lambdas can import any helper directly (e.g., `from backend.shared import chunk_text, embed_texts`).


## Frontend (`frontend/`)

- Next.js 16 / React 19 app styled with Mantine and Tabler icons.
- Persists chat sessions client-side so users can switch between existing sessions via the sidebar.
- Upload flow: when the user attaches files, the UI calls `/upload-url`, performs the direct PUT, then immediately calls `/ingest` before asking the question.
- Conversation view shows assistant answers plus cited chunks (source, page, similarity score).
- Environment: set `NEXT_PUBLIC_API_BASE_URL` to the API Gateway endpoint output by Terraform.
- Scripts:
  - `npm run dev` – start Next.js locally (defaults to `http://localhost:3000`).
  - `npm run build` / `npm run start` – production build & serve.
  - `npm run lint` – run ESLint per `eslint.config.mjs`.


## Lambda Layers (`layers/`)

### `layers/code`

- Mirrors `backend/shared` so every Lambda loads the same helper code without bundling duplicates.
- Packaged by Terraform (`layers.tf`) into `build/code_layer.zip`.
- Exposed via `aws_lambda_layer_version.code_layer`; attached to *all* lambdas.

### `layers/deps`

- Houses general-purpose Python dependencies (OpenAI SDK, tiktoken, pydantic, pypdf, httpx, etc.) installed under `deps/python`.
- Managed through `layers/deps/requirements.txt`.
- Archived as `build/other_deps_layer.zip` and published as the `other_deps_layer`.

### `layers/python`

- Contains heavier native libs (FAISS CPU, NumPy) laid out under `python/python/...` to match Lambda layer expectations.
- Requirements tracked in `layers/python/requirements.txt`.
- Packaged as `build/faiss_layer.zip` and used wherever FAISS is needed (all lambdas today for simplicity).

Update procedure: modify the relevant `requirements.txt` or code, rebuild the zip (`terraform apply` handles this automatically), and redeploy the layer. Remember to bump Lambda versions or reapply Terraform so functions pick up the new layer versions.


## Terraform Stack (`terraform/`)

### Core Files

- `main.tf` – pins Terraform (>=1.5) and AWS/Archive providers, sets common locals (project name, bucket, namespace, default OpenAI models), and fetches caller/region data.
- `variables.tf` – expects `project_name`, optional `region` (`us-east-1` default), and `openai_api_key` (sensitive).
- `output.tf` – surfaces `bucket_name`, `openai_secret_arn`, and `api_base_url` for downstream scripts/CI.

### Resource Modules

- `s3.tf` – creates the document bucket (`rag-docs-${project}`) plus strict public-access blocks and CORS allowing the local frontend origin (`http://localhost:3000`) for PUT/GET/HEAD.
- `secrets.tf` – provisions the `openai/api_key` secret and seeds it with the provided `var.openai_api_key`.
- `iam.tf` – defines the Lambda execution role (trusts `lambda.amazonaws.com`) and an inline policy granting:
  - S3 read/write/list on the bucket
  - Secrets Manager `GetSecretValue`
  - CloudWatch Logs create/write
  - DynamoDB CRUD/query on the messages table
- `dynamodb.tf` – creates a PAY_PER_REQUEST table `${project}-messages` keyed by `sessionKey` + `timestamp`, with PITR enabled.
- `layers.tf` – zips the three layer directories (`layers/code`, `layers/python`, `layers/deps`) and publishes them as versioned Lambda Layers.
- `lambda.tf` – packages each lambda folder via `archive_file`, defines five Lambda functions (memory/timeout tuned per workload), attaches the shared layers, and injects environment variables (bucket, namespace, secret ARN, embedding/chat models, Dynamo table name).
- `apigw.tf` – builds an HTTP API with CORS, configures integrations for each lambda, defines routes:
  - `POST /upload-url`
  - `POST /sessions`
  - `POST /ingest`
  - `POST /query`
  - `GET /sessions/{sessionId}/messages`
  Includes `$default` stage with auto deploy + access logs, and Lambda permissions so API Gateway can invoke each function.
- `layers/` (within `terraform/`) – holds the built layer artifacts once Terraform runs (mirrors source under the repo root to keep packaging deterministic).
- `build/` – Terraform writes ZIP outputs here; included in `.gitignore`.

### State & Variables

- `terraform.auto.tfvars` can store local defaults (e.g., `project_name`, `openai_api_key`), but keep secrets secure.
- `terraform.tfstate` / `.backup` capture deployed resource IDs; treat them as sensitive.


## Deployment & Operations

### Prerequisites

- Terraform ≥ 1.5
- Node.js ≥ 20 (for the Next.js app)
- AWS credentials with permissions for Lambda, API Gateway, S3, Secrets Manager, IAM, DynamoDB, and CloudWatch Logs in the chosen region (defaults to `us-east-1`).
- OpenAI API key.

### Provisioning AWS

```bash
cd terraform
terraform init
terraform plan \
  -var 'project_name=sail-demo' \
  -var 'openai_api_key=sk-...' \
  -out plan.out
terraform apply plan.out
```

Record the `bucket_name`, `openai_secret_arn`, and `api_base_url` outputs. Re-run `terraform apply` whenever you modify lambdas, layers, or infrastructure.

### Running the Frontend

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_BASE_URL="https://<api-id>.execute-api.us-east-1.amazonaws.com"
npm run dev
```

Visit `http://localhost:3000`, create/upload/chat. The UI automatically uploads `.txt` files, triggers ingest, and displays answer citations.

### Common Ops Tasks

- **Refreshing Layers** – edit `layers/*`, then `terraform apply` to rebuild and republish. Lambda versions will automatically pull the latest layer ARN.
- **Adding formats** – extend `backend/shared/chunking.py` and `backend/lambdas/ingest` to call `extract_pdf` or other parsers, then redeploy.
- **Troubleshooting** – check CloudWatch Logs for each lambda (`/aws/lambda/<project>-<fn>`). API errors (e.g., 404 for missing index) are forwarded to the client.
- **Re-ingesting** – delete `sessions/<id>/index/*` in S3 or upload new files; calling `/ingest` rebuilds the FAISS index for that session.


## Next Steps & Enhancements

- Add PDF ingestion paths
- Cognito auth
- Namespace per user isolation


