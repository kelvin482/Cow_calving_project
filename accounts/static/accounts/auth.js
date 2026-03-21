(() => {
    // Shared auth-page helpers live here so login, signup, and reset screens
    // can reuse the same pending-state and progress behavior.
    const authForm = document.querySelector("#auth-form");
    const actionButtons = Array.from(
        document.querySelectorAll("[data-submit-feedback]")
    );
    const progressFill = document.querySelector(".auth-progress-fill");
    const progressText = document.querySelector(".auth-progress-text");
    const progressFields = Array.from(
        document.querySelectorAll("[data-progress]")
    );

    const passwordInput = document.querySelector("#id_password1");
    const strengthBar = document.querySelector(".password-strength-bar");
    const loginTypeInputs = Array.from(
        document.querySelectorAll('input[name="login_type"]')
    );
    const loginModePanels = Array.from(
        document.querySelectorAll("[data-login-mode-panel]")
    );
    const googlePanels = Array.from(
        document.querySelectorAll("[data-login-mode-google]")
    );

    const resetActionButtons = () => {
        actionButtons.forEach((button) => {
            if (!(button instanceof HTMLButtonElement)) {
                return;
            }
            if (button.dataset.originalText) {
                button.textContent = button.dataset.originalText;
            }
            button.disabled = false;
            button.classList.remove("auth-button-pending");
            button.setAttribute("aria-busy", "false");
        });

        document.body.classList.remove("auth-page-pending");
    };

    const previewButtonPending = (button) => {
        if (!(button instanceof HTMLButtonElement)) {
            return;
        }

        // Show instant visual feedback on click, even while the browser is
        // still preparing the real form submit or external redirect.
        button.dataset.originalText = button.dataset.originalText || button.textContent;
        button.textContent = button.dataset.pendingText || "Please wait...";
        button.classList.add("auth-button-pending");
        button.setAttribute("aria-busy", "true");
    };

    const setButtonPending = (button) => {
        if (!(button instanceof HTMLButtonElement)) {
            return;
        }

        actionButtons.forEach((item) => {
            if (!(item instanceof HTMLButtonElement)) {
                return;
            }
            item.dataset.originalText = item.dataset.originalText || item.textContent;
            item.disabled = item !== button;
            if (item !== button) {
                item.textContent = item.dataset.originalText;
                item.classList.remove("auth-button-pending");
            }
        });

        previewButtonPending(button);
        button.classList.add("auth-button-pending");
        document.body.classList.add("auth-page-pending");
    };

    const updateProgress = () => {
        if (!progressFill || !progressText || progressFields.length === 0) {
            return;
        }

        const filled = progressFields.filter((field) => {
            if (field.type === "checkbox" || field.type === "radio") {
                return field.checked;
            }
            return String(field.value || "").trim().length > 0;
        }).length;

        const percent = Math.max(
            20,
            Math.round((filled / progressFields.length) * 100)
        );

        progressFill.style.width = `${percent}%`;
        progressText.textContent = `Step 1 of 1: ${filled} of ${progressFields.length} fields complete`;
    };

    const updateStrength = () => {
        if (!passwordInput || !strengthBar) {
            return;
        }

        const value = passwordInput.value || "";
        let score = 0;
        if (value.length >= 8) score += 1;
        if (/[A-Z]/.test(value)) score += 1;
        if (/[0-9]/.test(value)) score += 1;
        if (/[^A-Za-z0-9]/.test(value)) score += 1;

        const widths = ["25%", "45%", "65%", "85%", "100%"];
        strengthBar.style.width = widths[Math.min(score, widths.length - 1)];
        strengthBar.style.backgroundColor =
            score >= 3 ? "#2c5a42" : score >= 2 ? "#c9b7a3" : "#d16b5f";
    };

    const updateLoginMode = () => {
        if (loginTypeInputs.length === 0) {
            return;
        }

        const selectedInput = loginTypeInputs.find((input) => input.checked);
        const selectedMode = selectedInput ? selectedInput.value : "farmer";

        loginModePanels.forEach((panel) => {
            if (!(panel instanceof HTMLElement)) {
                return;
            }
            const shouldShow = panel.dataset.loginModePanel === selectedMode;
            panel.hidden = !shouldShow;
            panel.classList.toggle("hidden", !shouldShow);
        });

        googlePanels.forEach((panel) => {
            if (!(panel instanceof HTMLElement)) {
                return;
            }
            const shouldShow = selectedMode === "farmer";
            panel.hidden = !shouldShow;
            panel.classList.toggle("hidden", !shouldShow);
        });
    };

    document.addEventListener("input", (event) => {
        if (event.target.matches("[data-progress]")) {
            updateProgress();
        }
        if (event.target === passwordInput) {
            updateStrength();
        }
        if (event.target.matches('input[name="login_type"]')) {
            updateLoginMode();
        }
    });

    actionButtons.forEach((button) => {
        if (!(button instanceof HTMLButtonElement)) {
            return;
        }

        button.addEventListener("click", () => {
            document.body.classList.add("auth-page-pending");
            previewButtonPending(button);
        });
    });

    if (authForm instanceof HTMLFormElement) {
        authForm.addEventListener("submit", (event) => {
            const submitter = event.submitter;
            if (submitter instanceof HTMLButtonElement) {
                // Delay disabling until the browser has accepted the submit.
                // This avoids breaking the Google OAuth POST in browsers that
                // are sensitive to buttons being disabled too early.
                window.setTimeout(() => {
                    setButtonPending(submitter);
                }, 0);
            }
        });
    }

    window.addEventListener("pageshow", resetActionButtons);

    updateProgress();
    updateStrength();
    updateLoginMode();
    resetActionButtons();
})();
