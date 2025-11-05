"use client";

import { useState } from "react";
import {
  Alert,
  Button,
  Container,
  Group,
  List,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type UploadUrlResponse = {
  url: string;
  putHeaders?: Record<string, string>;
  key: string;
};

export default function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files ? Array.from(event.target.files) : [];
    setFiles(selected);
    setStatus(null);
    setError(null);
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

    setIsUploading(true);
    setStatus("Uploading files...");
    setError(null);

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
      setStatus(`Ingest complete: ${JSON.stringify(ingestJson)}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unexpected error during upload.";
      setError(message);
      setStatus(null);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <Title order={2}>Document Uploader</Title>
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <Text>Select one or more .txt files to upload:</Text>
            <input
              type="file"
              accept=".txt"
              multiple
              onChange={handleFileSelection}
            />
            {files.length > 0 && (
              <List size="sm" withPadding>
                {files.map((file) => (
                  <List.Item key={file.name}>{file.name}</List.Item>
                ))}
              </List>
            )}
            <Group justify="flex-start">
              <Button
                onClick={handleUpload}
                disabled={isUploading || files.length === 0}
              >
                Upload &amp; Ingest
              </Button>
              {isUploading && <Loader size="sm" />}
            </Group>
          </Stack>
        </Paper>

        {status && (
          <Alert color="blue" title="Status">
            {status}
          </Alert>
        )}

        {error && (
          <Alert color="red" title="Error" icon={<IconAlertCircle size={16} />}>
            {error}
          </Alert>
        )}
      </Stack>
    </Container>
  );
}
