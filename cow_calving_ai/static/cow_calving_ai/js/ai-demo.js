(() => {
    const form = document.getElementById("ai-form");
    const submitBtn = document.getElementById("submit-btn");
    const clearBtn = document.getElementById("clear-btn");
    const questionInput = document.getElementById("question");
    const cowIdInput = document.getElementById("cow-id");
    const statusEl = document.getElementById("status");
    const quickQuestions = document.getElementById("quick-questions");
    const chatLog = document.getElementById("chat-log");
    const aiEndpoint = form?.dataset.aiEndpoint || "/app/ai/test/";

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

    function addMessage(role, content, isMarkdown = false, scrollMode = "end") {
        const row = document.createElement("article");
        row.className = `chat-row ${role}`;

        const avatar = document.createElement("div");
        avatar.className = role === "assistant" ? "avatar avatar-assistant" : "avatar";
        avatar.textContent = role === "assistant" ? "AI" : "YOU";

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

        const avatar = document.createElement("div");
        avatar.className = "avatar avatar-assistant";
        avatar.textContent = "AI";

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
    }

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        questionInput.disabled = isLoading;
        submitBtn.textContent = isLoading ? "Thinking..." : "Send";
    }

    function autoresizeInput() {
        questionInput.style.height = "auto";
        questionInput.style.height = `${Math.min(questionInput.scrollHeight, 160)}px`;
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
        chatLog.innerHTML = "";
        addMessage(
            "assistant",
            "Chat cleared. Ask a new question whenever you are ready."
        );
        setStatus("Conversation cleared.");
    });

    quickQuestions.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) {
            return;
        }

        const question = target.dataset.question || "";
        if (!question) {
            return;
        }
        await submitQuestion(question);
    });

    questionInput.addEventListener("input", autoresizeInput);
    autoresizeInput();
})();
