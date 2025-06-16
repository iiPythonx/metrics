// Copyright (c) 2025 iiPython

// Handle logging
const log = (() => {
    const coreStyling = "color: #808080; padding: 5px 10px; border-radius: 5px; background-color:";
    const classifierColoring = {
        core: "#1a1a1a",
        api:  "#552020"
    };
    return (classifier, message) => {
        console.log(
            `%c${classifier}%c${message}`,
            coreStyling + classifierColoring[classifier.toLowerCase()],
            coreStyling + classifierColoring.core + "; margin-left: 5px"
        );
    };
})();

log("CORE", "iiPython Monitoring v0.1.0");

// Fetch endpoint information

