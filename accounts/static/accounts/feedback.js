(() => {
    // Auto-hide transient feedback banners so success/error messages do not
    // stay on screen after the user has already seen them.
    const messages = Array.from(
        document.querySelectorAll("[data-auto-dismiss-message]")
    );

    const dismissMessage = (message) => {
        if (!(message instanceof HTMLElement) || message.dataset.dismissed === "true") {
            return;
        }

        message.dataset.dismissed = "true";
        // Fade first, then collapse the space so nearby form content does not
        // jump abruptly when the banner disappears.
        message.style.transition =
            "opacity 220ms ease, transform 220ms ease, max-height 220ms ease, margin 220ms ease, padding 220ms ease";
        message.style.opacity = "0";
        message.style.transform = "translateY(-6px)";
        message.style.maxHeight = `${message.offsetHeight}px`;

        window.setTimeout(() => {
            message.style.maxHeight = "0";
            message.style.marginTop = "0";
            message.style.marginBottom = "0";
            message.style.paddingTop = "0";
            message.style.paddingBottom = "0";
            message.style.overflow = "hidden";
        }, 20);

        window.setTimeout(() => {
            message.remove();
        }, 260);
    };

    messages.forEach((message) => {
        const delay = Number.parseInt(message.dataset.dismissAfter || "5000", 10);
        // Keep the timeout configurable per banner while defaulting to the
        // shared 5-second feedback window used across the app.
        window.setTimeout(() => dismissMessage(message), Number.isNaN(delay) ? 5000 : delay);
    });
})();
