// Chat page helpers. The page still works without this file; it only makes it nicer.
(function () {
    const form = document.getElementById("chat-form");
    const box = document.getElementById("message");
    const button = document.getElementById("chat-send");
    const status = document.getElementById("chat-status");

    // Enter sends the message, Shift+Enter starts a new line.
    // isComposing is true while typing with an input method, where Enter means "accept".
    box.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            form.requestSubmit();
        }
    });

    // Loading indicator. It also stops the same message being sent twice.
    form.addEventListener("submit", function (event) {
        if (button.disabled || box.value.trim() === "") {
            event.preventDefault();
            box.focus();
            return;
        }
        button.disabled = true;
        box.readOnly = true; // readOnly, because a disabled box wouldn't be sent
        status.textContent = "Thinking...";
    });

    // Runs once the page has fully loaded, and again when the Back button restores it
    window.addEventListener("pageshow", function () {
        // Undo the loading state, in case the page was restored as it was
        button.disabled = false;
        box.readOnly = false;
        status.textContent = "";
        // Show the newest message and the message box
        form.scrollIntoView({ block: "end" });
    });
})();
