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

// HTTP status color calculations
const httpStatusColor = (code) => 200 <= code && code <= 299 ? "http-ok" : (code <= 399 ? "http-info" : "http-bad");

// Launch async session
(async () => {

    // Fetch node information
    const nodes = (await (await fetch("/v1/nodes")).json()).data;
    log("API", `Backend has ${nodes.length} node(s), ${nodes.filter(node => node.live).length} of which are active.`);

    while (nodes.length < 4) nodes.push({ icon: "-" });

    for (const node of nodes) {
        const element = document.createElement("article");
        if (!node.live) element.classList.add("dead-node");
        element.setAttribute("data-node-name", node.name);
        element.innerHTML = `
            <span>${node.icon}</span>
            <div>
                <span>${node.name || ''}</span>
                <span>${node.info || ''}</span>
            </div>
            <div>
                <span class = "tfb"></span>
                <span class = "rwl"></span>
            </div>
        `;
        document.getElementById("nodes").appendChild(element);
    }

    // Fetch metric information
    const metrics = (await (await fetch("/v1/metrics")).json()).data;
    log("API", `Retrieved latest metric data without issues.`);

    function load_tab(tab) {
        for (const tab of document.querySelectorAll("[data-tab]")) tab.classList.remove("active");
        document.querySelector(`[data-tab = "${tab}"]`).classList.add("active");

        const popupElement = document.getElementById("popup");

        // Handle empty data
        if (Object.keys(metrics[tab].nodes).length === 0) {
            for (const span of document.querySelectorAll("span[id]")) span.innerText = "N/A";
            document.getElementById("htc").classList = "";
            popupElement.style.display = "none";
            for (const elem of document.querySelectorAll(`[data-node-name]:not(.dead-node) .rwl`)) elem.innerText = `RWL: N/A`;
            for (const elem of document.querySelectorAll(`[data-node-name]:not(.dead-node) .tfb`)) elem.innerText = `TTFB: N/A`;
            return;
        }

        // Fetch overall data
        const overall = metrics[tab].overall;
        for (const field in overall) {
            if (field !== "htc") { document.getElementById(field).innerText = `${overall[field]}ms`; continue; }
            const name = {
                200: "OK",
                204: "No Content",
                301: "Moved Permanently",
                304: "Not Modified",
                307: "Temporary Redirect",
                400: "Bad Request",
                401: "Unauthorized",
                403: "Forbidden",
                404: "Not Found",
                405: "Method Not Allowed",
            }[overall[field]] || "";
            document.getElementById(field).innerText = `${overall[field]} ${name}`;
            document.getElementById(field).classList = httpStatusColor(overall[field]);
        };

        // Fetch per-node data
        popupElement.style.display = "flex";
        popupElement.innerHTML = "";

        for (const node in metrics[tab].nodes) {
            const data = metrics[tab].nodes[node];
            document.querySelector(`[data-node-name = "${node}"] .rwl`).innerText = `RWL: ${data.rwl}ms`;
            document.querySelector(`[data-node-name = "${node}"] .tfb`).innerText = `TTFB: ${data.tfb}ms`;

            // Create HTTP status popup
            const status = document.createElement("div");
            status.innerHTML = `<span>${nodes.filter(n => n.name === node)[0].icon}</span><span class = "${httpStatusColor(data.htc)}">${data.htc}</span>`;
            popupElement.appendChild(status);
        }
    }

    for (const endpoint in metrics) {
        const tab = document.createElement("span");
        tab.setAttribute("data-tab", endpoint);
        tab.innerText = endpoint;
        tab.addEventListener("click", () => load_tab(endpoint));
        document.querySelector("nav").appendChild(tab);
    }

    load_tab("Main");  // Temporary
})();
