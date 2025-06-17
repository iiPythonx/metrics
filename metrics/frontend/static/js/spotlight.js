// Copyright (c) 2025 iiPython

const light = document.getElementById("spotlight");
document.addEventListener("mousemove", (e) => {
    setTimeout(() => {
        light.style.setProperty("--x", `${e.clientX}px`);
        light.style.setProperty("--y", `${e.clientY}px`);
    }, 50);
});
