(() => {
    const cards = document.querySelectorAll("[data-kinetic-card]");
    if (!cards.length) {
        return;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

    const resetCard = (card) => {
        card.style.setProperty("--kinetic-rotate-x", "0deg");
        card.style.setProperty("--kinetic-rotate-y", "0deg");
        card.style.setProperty("--kinetic-pointer-x", "50%");
        card.style.setProperty("--kinetic-pointer-y", "50%");
        card.style.setProperty("--kinetic-press", "1");
    };

    const moveCard = (card, event) => {
        const rect = card.getBoundingClientRect();
        const x = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
        const y = Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1);
        const rotateX = (0.5 - y) * 12;
        const rotateY = (x - 0.5) * 14;

        card.style.setProperty("--kinetic-rotate-x", `${rotateX.toFixed(2)}deg`);
        card.style.setProperty("--kinetic-rotate-y", `${rotateY.toFixed(2)}deg`);
        card.style.setProperty("--kinetic-pointer-x", `${(x * 100).toFixed(2)}%`);
        card.style.setProperty("--kinetic-pointer-y", `${(y * 100).toFixed(2)}%`);
    };

    cards.forEach((card) => {
        resetCard(card);

        if (!finePointer.matches || reducedMotion.matches) {
            return;
        }

        card.addEventListener("pointermove", (event) => moveCard(card, event));
        card.addEventListener("pointerleave", () => resetCard(card));
        card.addEventListener("pointerdown", () => {
            card.style.setProperty("--kinetic-press", "0.985");
        });
        card.addEventListener("pointerup", () => {
            card.style.setProperty("--kinetic-press", "1");
        });
    });
})();
