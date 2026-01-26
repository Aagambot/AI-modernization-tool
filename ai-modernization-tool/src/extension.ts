import * as vscode from 'vscode';
import * as child_process from 'child_process';
import * as path from 'path';
import { SidebarProvider } from './SidebarProvider';

let pythonProcess: child_process.ChildProcess | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('AI Modernization Tool: Starting Backend...');

    // 1. Setup the Sidebar
    const provider = new SidebarProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            "ai-modernization-view", 
            provider
        )
    );

    // 2. Start the Python Sidecar Server
    // Note: This assumes server.py is in the parent directory of the extension
    const scriptPath = path.join(context.extensionPath, '..', 'server.py');
    const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';

    try {
        pythonProcess = child_process.spawn(pythonCommand, [scriptPath]);

        // Log Python output to the VS Code Developer Console
        pythonProcess.stdout?.on('data', (data: Buffer) => {
            console.log(`[Python Server]: ${data.toString()}`);
        });

        pythonProcess.stderr?.on('data', (data: Buffer) => {
            console.error(`[Python Error]: ${data.toString()}`);
        });

        vscode.window.showInformationMessage('Modernization Engine Started (Zero-Local Mode)');
    } catch (err) {
        vscode.window.showErrorMessage('Failed to launch Python server. Check Python path.');
    }
}

export function deactivate() {
    // 3. Cleanup: Kill the Python process when the extension is disabled
    if (pythonProcess) {
        pythonProcess.kill();
        console.log('AI Modernization Tool: Backend Stopped.');
    }
}