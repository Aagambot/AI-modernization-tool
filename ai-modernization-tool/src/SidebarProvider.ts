import * as vscode from 'vscode';
import axios from 'axios';

export class SidebarProvider implements vscode.WebviewViewProvider {
    constructor(private readonly _extensionUri: vscode.Uri) {}

    public resolveWebviewView(webviewView: vscode.WebviewView) {
        webviewView.webview.options = { 
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'onSearch': {
                    try {
                        const response = await axios.post('http://127.0.0.1:8000/ask', {
                            query: data.value
                        });

                        // Ensure we stringify the JSON object if the backend returns a dict
                        const answer = typeof response.data.answer === 'object' 
                            ? JSON.stringify(response.data.answer, null, 2) 
                            : response.data.answer;

                        webviewView.webview.postMessage({ 
                            type: 'showResponse', 
                            value: answer 
                        });
                    } catch (err) {
                        vscode.window.showErrorMessage("GraphRAG Server not responding.");
                        webviewView.webview.postMessage({ 
                            type: 'showResponse', 
                            value: "Error: Could not connect to backend logic engine." 
                        });
                    }
                    break;
                }
            }
        });
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        return `<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; 
                    style-src ${webview.cspSource} 'unsafe-inline'; 
                    script-src 'unsafe-inline'; 
                    connect-src http://127.0.0.1:8000 http://localhost:8000;">
                <style>
                    body { font-family: var(--vscode-font-family); padding: 10px; color: var(--vscode-foreground); }
                    #response { margin-top: 15px; white-space: pre-wrap; font-size: 11px; background: var(--vscode-textCodeBlock-background); padding: 8px; border-radius: 4px; overflow-x: auto; }
                    input { width: 100%; box-sizing: border-box; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); padding: 6px; margin-bottom: 8px; }
                    button { width: 100%; cursor: pointer; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 8px; margin-bottom: 4px; }
                    button:hover { background: var(--vscode-button-hoverBackground); }
                    .loader { color: var(--vscode-descriptionForeground); font-style: italic; margin-top: 10px; display: none; }
                    .quick-actions { margin-top: 15px; border-top: 1px solid var(--vscode-divider); pt: 10px; }
                    h4 { margin-bottom: 8px; color: var(--vscode-descriptionForeground); }
                </style>
            </head>
            <body>
                <h3>Sales Invoice Logic</h3>
                <input type="text" id="query" placeholder="Ask about Sales Invoice logic..." />
                <button id="searchBtn">Ask Agent</button>
                
                <div class="quick-actions">
                    <h4>Demo Shortcuts</h4>
                    <button onclick="quickQuery('Explain the validation logic in sales_invoice.py')">Explain Validation</button>
                    <button onclick="quickQuery('How are taxes calculated in this module?')">Analyze Tax Logic</button>
                    <button onclick="quickQuery('Show the call graph for the validate function')">Show Call Flow</button>
                </div>

                <div id="loader" class="loader">Querying GraphRAG Engine...</div>
                <div id="response"></div>

                <script>
                    const vscode = acquireVsCodeApi();
                    const responseDiv = document.getElementById('response');
                    const loader = document.getElementById('loader');

                    function quickQuery(text) {
                        document.getElementById('query').value = text;
                        sendRequest(text);
                    }

                    function sendRequest(query) {
                        responseDiv.innerHTML = '';
                        loader.style.display = 'block';
                        vscode.postMessage({ type: 'onSearch', value: query });
                    }

                    document.getElementById('searchBtn').addEventListener('click', () => {
                        sendRequest(document.getElementById('query').value);
                    });

                    window.addEventListener('message', event => {
                        const message = event.data;
                        if (message.type === 'showResponse') {
                            loader.style.display = 'none';
                            responseDiv.innerText = message.value;
                        }
                    });
                </script>
            </body>
            </html>`;
    }
}