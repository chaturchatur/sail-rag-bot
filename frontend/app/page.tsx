"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ActionIcon, Button, Loader, Text, Textarea } from "@mantine/core";
import {
  IconAlertCircle,
  IconFileText,
  IconMenu2,
  IconPlus,
  IconUpload,
  IconX,
  IconArrowUp,
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

// Message type for conversation history
type Message = {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  chunks?: QueryChunk[];
};

type QueryResponse = {
  answer: string;
  chunks: QueryChunk[];
  messages?: Message[];
};

type SessionMetadata = {
  title?: string;
  [key: string]: unknown;
};

type Session = {
  sessionId: string;
  createdAt?: string;
  manifestKey?: string;
  metadata?: SessionMetadata;
  namespace?: string;
};

type CreateSessionResponse = Session;

type GetMessagesResponse = {
  sessionId: string;
  messages: Message[];
  count: number;
};

const formatSessionLabel = (session: Session | null) => {
  if (!session) {
    return "session";
  }

  if (
    session.metadata &&
    typeof session.metadata.title === "string" &&
    session.metadata.title.trim().length > 0
  ) {
    return session.metadata.title;
  }

  return `chat ${session.sessionId.slice(0, 8)}`;
};

export default function HomePage() {
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [sessionUploads, setSessionUploads] = useState<
    Record<string, string[]>
  >({});
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [hasSessionAttempted, setHasSessionAttempted] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // NEW: Store messages per session
  const [sessionMessages, setSessionMessages] = useState<
    Record<string, Message[]>
  >({});

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const hasSession = activeSessionId !== null;
  const activeSession = hasSession
    ? sessions.find((session) => session.sessionId === activeSessionId) ?? null
    : null;
  const uploadedFiles = activeSession
    ? sessionUploads[activeSession.sessionId] ?? []
    : [];

  // Get messages for active session
  const messages = activeSession
    ? sessionMessages[activeSession.sessionId] ?? []
    : [];

  const isUploadInProgress = isUploading || isQuerying;
  const isBusy = isUploadInProgress || isCreatingSession;

  const sidebarClassName = `${classes.sidebar} ${
    isSidebarOpen ? classes.sidebarExpanded : classes.sidebarCollapsed
  }`;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Load messages from API
  const loadMessages = useCallback(
    async (sessionId: string) => {
      if (!API_BASE_URL) {
        return;
      }

      setIsLoadingMessages(true);

      try {
        const res = await fetch(
          `${API_BASE_URL}/sessions/${sessionId}/messages`,
          {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          }
        );

        if (!res.ok) {
          throw new Error(`Failed to load messages: ${res.statusText}`);
        }

        const data = (await res.json()) as GetMessagesResponse;

        setSessionMessages((prev) => ({
          ...prev,
          [sessionId]: data.messages || [],
        }));
      } catch (err) {
        console.error("Error loading messages:", err);
        // Don't show error to user for message loading failures
        // Just default to empty messages
        setSessionMessages((prev) => ({
          ...prev,
          [sessionId]: [],
        }));
      } finally {
        setIsLoadingMessages(false);
      }
    },
    [API_BASE_URL]
  );

  const createSession = useCallback(async () => {
    if (!API_BASE_URL) {
      setError("NEXT_PUBLIC_API_BASE_URL is not set.");
      return;
    }

    setIsCreatingSession(true);
    setStatus("Creating new chat...");
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        throw new Error(`Failed to create session: ${res.statusText}`);
      }

      const data = (await res.json()) as CreateSessionResponse;

      const session: Session = {
        sessionId: data.sessionId,
        createdAt: data.createdAt,
        manifestKey: data.manifestKey,
        metadata: data.metadata,
        namespace: data.namespace,
      };

      setSessions((prev) => {
        const filtered = prev.filter(
          (item) => item.sessionId !== session.sessionId
        );
        return [session, ...filtered];
      });

      setActiveSessionId(session.sessionId);
      setSessionUploads((prev) => {
        if (prev[session.sessionId]) {
          return prev;
        }
        return { ...prev, [session.sessionId]: [] };
      });

      // Initialize empty messages for new session
      setSessionMessages((prev) => ({
        ...prev,
        [session.sessionId]: [],
      }));

      setMessage("");
      setPendingFiles([]);
      setStatus(`Created ${formatSessionLabel(session)}.`);
    } catch (err) {
      const details =
        err instanceof Error ? err.message : "Unable to create session.";
      setStatus(null);
      setError(details);
      setHasSessionAttempted(true);
    } finally {
      setIsCreatingSession(false);
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    if (!API_BASE_URL) {
      setError("NEXT_PUBLIC_API_BASE_URL is not set.");
      return;
    }

    if (!hasSessionAttempted && sessions.length === 0 && !isCreatingSession) {
      setHasSessionAttempted(true);
      void createSession();
    }
  }, [
    API_BASE_URL,
    createSession,
    hasSessionAttempted,
    isCreatingSession,
    sessions.length,
  ]);

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files ? Array.from(event.target.files) : [];

    if (!hasSession) {
      setError("Create or select a chat session before attaching files.");
      event.target.value = "";
      return;
    }

    if (selected.length === 0) {
      return;
    }

    setPendingFiles((prev) => {
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

  const handleRemovePendingFile = (fileToRemove: File) => {
    setPendingFiles((prev) =>
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
    if (!hasSession) {
      setError("Create or select a chat session first.");
      return;
    }

    fileInputRef.current?.click();
  };

  const handleSelectSession = (sessionId: string) => {
    if (sessionId === activeSessionId || isBusy) {
      return;
    }

    const session =
      sessions.find((item) => item.sessionId === sessionId) ?? null;

    setActiveSessionId(sessionId);
    setMessage("");
    setPendingFiles([]);
    setError(null);
    setSessionUploads((prev) => {
      if (prev[sessionId]) {
        return prev;
      }
      return { ...prev, [sessionId]: [] };
    });

    // Load messages if we haven't loaded them yet
    if (!sessionMessages[sessionId]) {
      void loadMessages(sessionId);
    }

    if (session) {
      setStatus(`Switched to ${formatSessionLabel(session)}.`);
    } else {
      setStatus(null);
    }
  };

  const handleTextareaKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!hasSession) {
        setError("Create or select a chat session first.");
        return;
      }

      if (!isBusy) {
        void handleSubmit();
      }
    }
  };

  const runQuery = async (question: string, session: Session) => {
    if (!API_BASE_URL) {
      setError("NEXT_PUBLIC_API_BASE_URL is not set.");
      return;
    }

    setIsQuerying(true);
    setStatus(`Searching ${formatSessionLabel(session)}...`);
    setError(null);

    try {
      const queryRes = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, sessionId: session.sessionId }),
      });

      if (queryRes.status === 404) {
        const payload = (await queryRes.json()) as { error?: string };
        setError(
          payload.error ??
            "No index found for this chat. Upload documents and ingest first."
        );
        setStatus(null);
        return;
      }

      if (!queryRes.ok) {
        throw new Error(`Query failed: ${queryRes.statusText}`);
      }

      const data = (await queryRes.json()) as QueryResponse;

      // Update messages from response
      if (data.messages && data.messages.length > 0) {
        setSessionMessages((prev) => ({
          ...prev,
          [session.sessionId]: data.messages!,
        }));
      }

      setStatus(null);
    } catch (err) {
      const details =
        err instanceof Error ? err.message : "Unexpected error while querying.";
      setError(details);
      setStatus(null);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleSubmit = async () => {
    if (!API_BASE_URL) {
      setError("NEXT_PUBLIC_API_BASE_URL is not set.");
      return;
    }

    const session = activeSession;

    if (!session) {
      setError("Create or select a chat session first.");
      return;
    }

    const question = message.trim();

    if (!question) {
      setError("Type a question before asking.");
      return;
    }

    const sessionLabel = formatSessionLabel(session);

    setError(null);

    // Immediately add user message to UI
    const userMessage: Message = {
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };

    setSessionMessages((prev) => ({
      ...prev,
      [session.sessionId]: [...(prev[session.sessionId] || []), userMessage],
    }));

    // Clear input immediately
    setMessage("");

    if (pendingFiles.length > 0) {
      setIsUploading(true);
      setStatus(`Uploading files for ${sessionLabel}...`);

      try {
        for (const file of pendingFiles) {
          setStatus(`Uploading ${file.name} to ${sessionLabel}...`);

          const uploadUrlRes = await fetch(`${API_BASE_URL}/upload-url`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId: session.sessionId,
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

        setStatus(
          `All files uploaded for ${sessionLabel}. Triggering ingest...`
        );

        const ingestRes = await fetch(`${API_BASE_URL}/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sessionId: session.sessionId }),
        });

        if (!ingestRes.ok) {
          throw new Error(`Ingest failed: ${ingestRes.statusText}`);
        }

        const ingestJson = (await ingestRes.json()) as {
          stats?: { chunks?: number };
        };

        const chunkCount = ingestJson.stats?.chunks ?? 0;
        setStatus(
          `Ingest complete for ${sessionLabel}: ${chunkCount} chunks. Asking your question...`
        );

        setSessionUploads((prev) => {
          const already = prev[session.sessionId] ?? [];
          const newNames = pendingFiles.map((file) => file.name);
          const merged = Array.from(new Set([...already, ...newNames]));
          return { ...prev, [session.sessionId]: merged };
        });
      } catch (err) {
        const details =
          err instanceof Error
            ? err.message
            : "Unexpected error during upload.";
        setError(details);
        setStatus(null);
        setIsUploading(false);
        return;
      } finally {
        setIsUploading(false);
      }
    }

    await runQuery(question, session);
    setPendingFiles([]);
  };

  return (
    <div className={classes.app}>
      <aside className={sidebarClassName}>
        <div className={classes.sidebarContent}>
          <div className={classes.sidebarHeader}>
            <ActionIcon
              variant="subtle"
              size="lg"
              radius="xl"
              className={classes.sidebarToggle}
              onClick={() => setIsSidebarOpen((prev) => !prev)}
            >
              <IconMenu2 size={18} />
            </ActionIcon>

            <button
              type="button"
              className={`${classes.sidebarNewChatButton} ${
                isSidebarOpen
                  ? classes.sidebarNewChatExpanded
                  : classes.sidebarNewChatCollapsed
              }`}
              onClick={() => {
                if (!isBusy) {
                  void createSession();
                }
              }}
              disabled={isBusy}
            >
              <IconPlus size={16} />
              {isSidebarOpen && (
                <span className={classes.sidebarNewChatLabel}>
                  {isCreatingSession ? "Creating..." : "New chat"}
                </span>
              )}
            </button>
          </div>

          <div className={classes.sidebarSection}>
            {isSidebarOpen && (
              <Text className={classes.sidebarSectionHeading}>
                Recent Chats
              </Text>
            )}
            <div className={classes.sessionList}>
              {sessions.map((session, index) => {
                const isActive = session.sessionId === activeSessionId;
                const label =
                  session.metadata?.title ?? `Chat ${sessions.length - index}`;

                return (
                  <button
                    type="button"
                    key={session.sessionId}
                    className={`${classes.sessionChip} ${
                      isActive ? classes.sessionChipActive : ""
                    }`}
                    onClick={() => handleSelectSession(session.sessionId)}
                    disabled={
                      (isUploadInProgress && !isActive) || isCreatingSession
                    }
                  >
                    <span className={classes.sessionChipText}>
                      <span className={classes.sessionChipLabel}>{label}</span>
                      <span className={classes.sessionChipId}>
                        {session.sessionId.slice(0, 8)}
                      </span>
                    </span>
                  </button>
                );
              })}

              {sessions.length === 0 && (
                <Text size="sm" className={classes.sessionEmpty}>
                  {isCreatingSession
                    ? "Creating your first chat..."
                    : "No chats yet. Start a new one to begin."}
                </Text>
              )}
            </div>
          </div>
        </div>
      </aside>

      <div className={classes.page}>
        <header className={classes.topBar}>
          <Text className={classes.brand}>Sail</Text>
        </header>

        <main className={classes.main}>
          {messages.length === 0 && !isLoadingMessages && (
            <div className={classes.mainHeader}>
              <Text className={classes.greeting}>Hello, Ritvik</Text>
            </div>
          )}

          {/* Conversation messages */}
          {messages.length > 0 && (
            <div className={classes.conversationContainer}>
              {messages.map((msg, index) => (
                <div
                  key={`${msg.timestamp}-${index}`}
                  className={
                    msg.role === "user"
                      ? classes.userMessage
                      : classes.assistantMessage
                  }
                >
                  <div className={classes.messageContent}>
                    <Text className={classes.messageText}>{msg.content}</Text>
                  </div>

                  {/* Show sources for assistant messages */}
                  {msg.role === "assistant" &&
                    msg.chunks &&
                    msg.chunks.length > 0 && (
                      <div className={classes.messageSources}>
                        <Text className={classes.sourcesHeading}>Sources</Text>
                        {msg.chunks.map((chunk, chunkIndex) => {
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
                              key={`${chunk.source ?? "source"}-${chunkIndex}`}
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
              ))}

              {/* Typing indicator */}
              {isQuerying && (
                <div className={classes.assistantMessage}>
                  <div className={classes.messageContent}>
                    <Loader size="sm" />
                    <Text className={classes.typingText}>Thinking...</Text>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {isLoadingMessages && (
            <div className={classes.statusCard}>
              <Loader size="sm" />
              <Text size="sm">Loading conversation...</Text>
            </div>
          )}

          {/* Query input card - fixed at bottom */}
          <div className={classes.queryCard}>
            <div className={classes.queryBody}>
              <div className={classes.queryInputRow}>
                <Textarea
                  placeholder={
                    hasSession
                      ? "Ask Sail"
                      : "Create a chat to start asking questions"
                  }
                  autosize
                  minRows={1}
                  maxRows={4}
                  value={message}
                  onChange={(event) => setMessage(event.currentTarget.value)}
                  onKeyDown={handleTextareaKeyDown}
                  disabled={isCreatingSession || !hasSession}
                  classNames={{
                    root: classes.textareaRoot,
                    input: classes.textarea,
                  }}
                />
                <ActionIcon
                  variant="filled"
                  radius="xl"
                  size="lg"
                  className={classes.askAction}
                  onClick={() => void handleSubmit()}
                  disabled={
                    !hasSession || isBusy || message.trim().length === 0
                  }
                  aria-label="Ask"
                >
                  {isUploadInProgress ? (
                    <Loader size="sm" />
                  ) : pendingFiles.length > 0 ? (
                    <IconUpload size={16} />
                  ) : (
                    <IconArrowUp size={16} />
                  )}
                </ActionIcon>
              </div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              multiple
              disabled={!hasSession}
              className={classes.hiddenInput}
              onChange={handleFileSelection}
            />

            {pendingFiles.length > 0 && (
              <div className={classes.attachments}>
                {pendingFiles.map((file) => (
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
                      onClick={() => handleRemovePendingFile(file)}
                      aria-label={`Remove ${file.name}`}
                    >
                      <IconX size={12} />
                    </ActionIcon>
                  </div>
                ))}
              </div>
            )}

            {uploadedFiles.length > 0 && (
              <div className={classes.uploadedSection}>
                <Text className={classes.uploadedHeading}>Uploaded</Text>
                <div className={classes.uploadedList}>
                  {uploadedFiles.map((fileName) => (
                    <div
                      key={fileName}
                      className={classes.uploadedChip}
                      title={fileName}
                    >
                      <IconFileText size={14} />
                      <Text size="xs" className={classes.uploadedChipLabel}>
                        {fileName}
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className={classes.queryControls}>
              <Button
                radius="xl"
                variant="subtle"
                className={classes.attachButton}
                leftSection={<IconPlus size={16} />}
                onClick={handleOpenFilePicker}
                disabled={!hasSession || isBusy}
              >
                Attach files
              </Button>
            </div>
          </div>

          {status && (
            <div className={classes.statusCard}>
              {(isUploadInProgress || isCreatingSession) && (
                <Loader size="sm" />
              )}
              <Text size="sm">{status}</Text>
            </div>
          )}

          {error && (
            <div className={classes.errorCard}>
              <IconAlertCircle size={16} />
              <Text size="sm">{error}</Text>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
