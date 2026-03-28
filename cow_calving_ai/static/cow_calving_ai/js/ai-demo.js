(() => {
    const form = document.getElementById("ai-form");
    const submitBtn = document.getElementById("submit-btn");
    const clearBtn = document.getElementById("clear-btn");
    const questionInput = document.getElementById("question");
    const cowIdInput = document.getElementById("cow-id");
    const statusEl = document.getElementById("status");
    const quickQuestions = document.getElementById("quick-questions");
    const quickPromptsToggle = document.querySelector("[data-quick-prompts-toggle]");
    const quickPromptsPanel = document.getElementById("quick-prompts-panel");
    const chatLog = document.getElementById("chat-log");
    const aiEndpoint = form?.dataset.aiEndpoint || "/app/ai/test/";
    const initialChatMarkup = chatLog?.innerHTML || "";

    function setQuickPromptsOpen(isOpen) {
        if (!quickPromptsToggle || !quickPromptsPanel) {
            return;
        }

        quickPromptsPanel.hidden = !isOpen;
        quickPromptsToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        quickPromptsToggle.textContent = isOpen ? "Hide prompts" : "Show prompts";
    }

    function setStatus(message, isError = false) {
        statusEl.textContent = message;
        statusEl.classList.toggle("status-error", isError);
        statusEl.classList.toggle("status-normal", !isError);
    }

    function escapeHtml(text) {
        return text
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function renderInlineMarkdown(text) {
        let safe = escapeHtml(text);
        safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
        safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        safe = safe.replace(/\*([^*]+)\*/g, "<em>$1</em>");
        return safe;
    }

    function renderMarkdown(text) {
        const lines = (text || "").replace(/\r\n/g, "\n").split("\n");
        const html = [];
        let i = 0;

        while (i < lines.length) {
            const rawLine = lines[i];
            const line = rawLine.trim();

            if (!line) {
                i += 1;
                continue;
            }

            const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
            if (headingMatch) {
                const level = headingMatch[1].length;
                const content = renderInlineMarkdown(headingMatch[2]);
                html.push(`<h${level}>${content}</h${level}>`);
                i += 1;
                continue;
            }

            const numberedSectionMatch = line.match(/^(\d+)\)\s+(.*)$/);
            if (numberedSectionMatch) {
                const content = renderInlineMarkdown(
                    `${numberedSectionMatch[1]}) ${numberedSectionMatch[2]}`
                );
                html.push(`<h3 class="section-heading">${content}</h3>`);
                i += 1;
                continue;
            }

            if (/^[-*]\s+/.test(line)) {
                const listItems = [];
                while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
                    const item = lines[i].trim().replace(/^[-*]\s+/, "");
                    listItems.push(`<li>${renderInlineMarkdown(item)}</li>`);
                    i += 1;
                }
                html.push(`<ul>${listItems.join("")}</ul>`);
                continue;
            }

            if (/^\d+\.\s+/.test(line)) {
                const listItems = [];
                while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
                    const item = lines[i].trim().replace(/^\d+\.\s+/, "");
                    listItems.push(`<li>${renderInlineMarkdown(item)}</li>`);
                    i += 1;
                }
                html.push(`<ol>${listItems.join("")}</ol>`);
                continue;
            }

            html.push(`<p>${renderInlineMarkdown(line)}</p>`);
            i += 1;
        }

        return html.join("");
    }

    function buildAvatar(role) {
        const avatar = document.createElement("div");
        avatar.className = role === "assistant" ? "avatar avatar-assistant" : "avatar";
        avatar.setAttribute("aria-hidden", "true");

        avatar.innerHTML =
            role === "assistant"
                ? `
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M9 3.5h6M12 3.5v2.25M6.75 9.25h10.5c.97 0 1.75.78 1.75 1.75v5.25c0 .97-.78 1.75-1.75 1.75H6.75A1.75 1.75 0 0 1 5 16.25V11c0-.97.78-1.75 1.75-1.75Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"></path>
                        <path d="M8.75 13h.01M15.25 13h.01M9.75 16h4.5M5 12 3.75 10.75M19 12l1.25-1.25" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"></path>
                    </svg>
                `
                : `
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M12 12a3.25 3.25 0 1 0 0-6.5 3.25 3.25 0 0 0 0 6.5Z" stroke="currentColor" stroke-width="1.7"></path>
                        <path d="M5.5 19.25c0-3.04 2.92-5.5 6.5-5.5s6.5 2.46 6.5 5.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"></path>
                    </svg>
                `;

        return avatar;
    }

    function addMessage(role, content, isMarkdown = false, scrollMode = "end") {
        const row = document.createElement("article");
        row.className = `chat-row ${role}`;

        const avatar = buildAvatar(role);

        const bubble = document.createElement("div");
        bubble.className =
            role === "assistant"
                ? "bubble bubble-assistant markdown"
                : "bubble bubble-user";
        if (isMarkdown) {
            bubble.innerHTML = renderMarkdown(content);
        } else {
            bubble.textContent = content;
        }

        row.append(avatar, bubble);
        chatLog.appendChild(row);
        if (scrollMode === "start") {
            row.scrollIntoView({ behavior: "smooth", block: "start" });
        } else {
            chatLog.scrollTop = chatLog.scrollHeight;
        }
        return row;
    }

    function addTypingMessage() {
        const row = document.createElement("article");
        row.className = "chat-row assistant";

        const avatar = buildAvatar("assistant");

        const bubble = document.createElement("div");
        bubble.className = "bubble bubble-assistant";
        bubble.innerHTML = `
            <span class="typing" aria-label="AI is thinking">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </span>
        `;
        row.append(avatar, bubble);
        chatLog.appendChild(row);
        chatLog.scrollTop = chatLog.scrollHeight;
        return row;
    }

    function wait(ms) {
        return new Promise((resolve) => {
            setTimeout(resolve, ms);
        });
    }

    function resetComposer() {
        questionInput.value = "";
        questionInput.style.height = "auto";
        questionInput.style.overflowY = "hidden";
    }

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        questionInput.disabled = isLoading;
        submitBtn.textContent = isLoading ? "Thinking..." : "Ask AI";
    }

    function autoresizeInput() {
        questionInput.style.height = "auto";
        const nextHeight = Math.min(questionInput.scrollHeight, 160);
        questionInput.style.height = `${nextHeight}px`;
        questionInput.style.overflowY =
            questionInput.scrollHeight > 160 ? "auto" : "hidden";
    }

    async function fetchAdvice(question, cowId) {
        const params = new URLSearchParams({ q: question });
        if (cowId) {
            params.set("cow_id", cowId);
        }

        const response = await fetch(`${aiEndpoint}?${params.toString()}`, {
            method: "GET",
            headers: {
                Accept: "application/json",
            },
        });

        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            const body = await response.text();
            if (body.includes("<!DOCTYPE") || body.includes("<html")) {
                throw new Error("The AI endpoint returned an HTML page instead of JSON.");
            }
            throw new Error("The AI endpoint returned an unexpected response format.");
        }

        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.error || "Request failed.");
        }
        return payload;
    }

    async function submitQuestion(question) {
        const cowId = (cowIdInput?.value || "").trim();
        addMessage("user", question, false, "end");
        setLoading(true);
        setStatus("Sending request...");
        const typingRow = addTypingMessage();
        const requestStart = performance.now();

        try {
            const payload = await fetchAdvice(question, cowId);
            const elapsed = performance.now() - requestStart;
            if (elapsed < 350) {
                await wait(350 - elapsed);
            }
            typingRow.remove();
            addMessage(
                "assistant",
                payload.advice || "No response returned.",
                true,
                "start"
            );
            setStatus("Response received.");
        } catch (error) {
            typingRow.remove();
            addMessage("assistant", "No response available.", false, "start");
            setStatus(error.message || "Failed to fetch advice.", true);
        } finally {
            setLoading(false);
            resetComposer();
            questionInput.focus();
        }
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const question = questionInput.value.trim();

        if (!question) {
            setStatus("Please enter a question first.", true);
            return;
        }

        await submitQuestion(question);
    });

    clearBtn.addEventListener("click", () => {
        chatLog.innerHTML = initialChatMarkup;
        setStatus("Conversation cleared.");
        setQuickPromptsOpen(false);
        resetComposer();
        questionInput.focus();
    });

    quickPromptsToggle?.addEventListener("click", () => {
        const isExpanded =
            quickPromptsToggle.getAttribute("aria-expanded") === "true";
        setQuickPromptsOpen(!isExpanded);
    });

    quickQuestions?.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) {
            return;
        }

        const question = target.dataset.question || "";
        if (!question) {
            return;
        }

        setQuickPromptsOpen(false);
        await submitQuestion(question);
    });

    // Match the familiar chat pattern where Enter sends and Shift+Enter keeps
    // a manual line break for longer notes.
    questionInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.shiftKey) {
            return;
        }

        event.preventDefault();
        form.requestSubmit();
    });

    questionInput.addEventListener("input", autoresizeInput);
    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Element) || !quickPromptsPanel || quickPromptsPanel.hidden) {
            return;
        }

        if (
            target.closest("[data-quick-prompts-toggle]") ||
            target.closest("#quick-prompts-panel")
        ) {
            return;
        }

        setQuickPromptsOpen(false);
    });
    autoresizeInput();
    setQuickPromptsOpen(false);
})();
