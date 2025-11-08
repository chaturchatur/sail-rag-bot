"use client";

import { useRef, useState } from "react";
import { ActionIcon, Button, Loader, Text, Textarea } from "@mantine/core";
import {
  IconAlertCircle,
  IconFileText,
  IconPlus,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import classes from "./page.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type UploadUrlResponse = {
  url: string;
  putHeaders?: Record<string, string>;
  key: string;
};

type QueryChunk = {
  text: string;
  source?: string | null;
  page?: number | null;
  score?: number;
};

type QueryResponse = {
  answer: string;
  chunks: QueryChunk[];
};

export default function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [chunks, setChunks] = useState<QueryChunk[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files ? Array.from(event.target.files) : [];

    if (selected.length === 0) {
      return;
    }

    setFiles((prev) => {
      const existingKeys = new Set(
        prev.map((file) => `${file.name}-${file.size}-${file.lastModified}`)
      );
      const merged = [...prev];

      selected.forEach((file) => {
        const key = `${file.name}-${file.size}-${file.lastModified}`;
        if (!existingKeys.has(key)) {
          merged.push(file);
          existingKeys.add(key);
        }
      });

      return merged;
    });

    setStatus(null);
    setError(null);
    event.target.value = "";
  };

  const handleRemoveFile = (fileToRemove: File) => {
    setFiles((prev) =>
      prev.filter(
        (file) =>
          !(
            file.name === fileToRemove.name &&
            file.size === fileToRemove.size &&
            file.lastModified === fileToRemove.lastModified
          )
      )
    );
  };

  const handleOpenFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleTextareaKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!isUploading && !isQuerying) {
        void handleUpload();
      }
    }
  };

  const runQuery = async (question: string) => {
    setIsQuerying(true);
    setStatus("Searching indexed documents...");
    setError(null);
    setAnswer(null);
    setChunks([]);

    try {
      const queryRes = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!queryRes.ok) {
        throw new Error(`Query failed: ${queryRes.statusText}`);
      }

      const data = (await queryRes.json()) as QueryResponse;
      setAnswer(data.answer ?? "");
      setChunks(data.chunks ?? []);
    } catch (err) {
      const details =
        err instanceof Error ? err.message : "Unexpected error while querying.";
      setError(details);
    } finally {
      setIsQuerying(false);
      setStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!API_BASE_URL) {
      setError("NEXT_PUBLIC_API_BASE_URL is not set.");
      return;
    }

    if (files.length === 0) {
      setError("Choose at least one .txt file first.");
      return;
    }

    const question = message.trim();

    if (!question) {
      setError("Type a question before uploading.");
      return;
    }

    setIsUploading(true);
    setStatus("Uploading files...");
    setError(null);
    setAnswer(null);
    setChunks([]);

    try {
      for (const file of files) {
        setStatus(`Uploading ${file.name}...`);

        const uploadUrlRes = await fetch(`${API_BASE_URL}/upload-url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            contentType: file.type || "text/plain",
          }),
        });

        if (!uploadUrlRes.ok) {
          throw new Error(
            `Failed to get upload URL for ${file.name}: ${uploadUrlRes.statusText}`
          );
        }

        const { url, putHeaders }: UploadUrlResponse =
          await uploadUrlRes.json();

        const putRes = await fetch(url, {
          method: "PUT",
          body: file,
          headers: putHeaders ?? {
            "Content-Type": file.type || "application/octet-stream",
          },
        });

        if (!putRes.ok) {
          throw new Error(
            `PUT to S3 failed for ${file.name}: ${putRes.statusText}`
          );
        }
      }

      setStatus("All files uploaded. Triggering ingest...");
      const ingestRes = await fetch(`${API_BASE_URL}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!ingestRes.ok) {
        throw new Error(`Ingest failed: ${ingestRes.statusText}`);
      }

      const ingestJson = await ingestRes.json();
      setStatus(
        `Ingest complete: ${JSON.stringify(
          ingestJson
        )}. Asking your question...`
      );
      await runQuery(question);
      setMessage("");
      setFiles([]);
    } catch (err) {
      const details =
        err instanceof Error ? err.message : "Unexpected error during upload.";
      setError(details);
      setStatus(null);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={classes.page}>
      <header className={classes.topBar}>
        <Text className={classes.brand}>Sail</Text>
      </header>

      <main className={classes.main}>
        <Text className={classes.greeting}>Hello, Ritvik</Text>

        <div className={classes.queryCard}>
          <div className={classes.queryBody}>
            <Textarea
              placeholder="Ask Sail"
              autosize
              minRows={1}
              maxRows={4}
              value={message}
              onChange={(event) => setMessage(event.currentTarget.value)}
              onKeyDown={handleTextareaKeyDown}
              classNames={{
                root: classes.textareaRoot,
                input: classes.textarea,
              }}
            />
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            multiple
            className={classes.hiddenInput}
            onChange={handleFileSelection}
          />

          {files.length > 0 && (
            <div className={classes.attachments}>
              {files.map((file) => (
                <div
                  className={classes.attachment}
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                >
                  <IconFileText size={14} />
                  <Text size="xs" className={classes.attachmentLabel}>
                    {file.name}
                  </Text>
                  <ActionIcon
                    size="sm"
                    variant="subtle"
                    className={classes.removeAttachment}
                    onClick={() => handleRemoveFile(file)}
                    aria-label={`Remove ${file.name}`}
                  >
                    <IconX size={12} />
                  </ActionIcon>
                </div>
              ))}
            </div>
          )}

          <div className={classes.queryControls}>
            <Button
              radius="xl"
              variant="subtle"
              className={classes.attachButton}
              leftSection={<IconPlus size={16} />}
              onClick={handleOpenFilePicker}
            >
              Attach files
            </Button>

            <Button
              radius="xl"
              className={classes.uploadButton}
              onClick={() => void handleUpload()}
              disabled={isUploading || isQuerying || files.length === 0}
              leftSection={
                isUploading || isQuerying ? (
                  <Loader size="xs" />
                ) : (
                  <IconUpload size={16} />
                )
              }
            >
              {isUploading || isQuerying ? "Uploading & asking..." : "Upload"}
            </Button>
          </div>
        </div>

        {status && (
          <div className={classes.statusCard}>
            {(isUploading || isQuerying) && <Loader size="sm" />}
            <Text size="sm">{status}</Text>
          </div>
        )}

        {error && (
          <div className={classes.errorCard}>
            <IconAlertCircle size={16} />
            <Text size="sm">{error}</Text>
          </div>
        )}

        {answer && (
          <div className={classes.answerCard}>
            <Text className={classes.answerHeading}>Answer</Text>
            <Text className={classes.answerText}>{answer}</Text>

            {chunks.length > 0 && (
              <div className={classes.sourceList}>
                <Text className={classes.answerHeading}>Sources</Text>
                {chunks.map((chunk, index) => {
                  const metaParts = [
                    chunk.source || "Unknown source",
                    chunk.page !== null && chunk.page !== undefined
                      ? `page ${chunk.page}`
                      : null,
                    typeof chunk.score === "number"
                      ? `score ${chunk.score.toFixed(3)}`
                      : null,
                  ].filter(Boolean);

                  return (
                    <div
                      key={`${chunk.source ?? "source"}-${index}`}
                      className={classes.sourceItem}
                    >
                      <Text className={classes.sourceLabel}>
                        {metaParts.join(" • ")}
                      </Text>
                      <Text size="sm" className={classes.sourceText}>
                        {chunk.text}
                      </Text>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
