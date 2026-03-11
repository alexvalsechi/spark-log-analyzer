const path = require('path');
const fs = require('fs/promises');
const os = require('os');
const { execFile } = require('child_process');
const { app, BrowserWindow } = require('electron');
const { ipcMain } = require('electron');

function runFile(command, args, cwd) {
  return new Promise((resolve, reject) => {
    execFile(command, args, { cwd }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(`Command failed: ${stderr || error.message}`));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 980,
    minHeight: 680,
    autoHideMenuBar: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  ipcMain.handle('reduce-zip-locally', async (_event, payload) => {
    const zipPath = payload && payload.zipPath;
    const compact = !!(payload && payload.compact);

    if (!zipPath) {
      throw new Error('zipPath is required');
    }

    const outputFile = path.join(os.tmpdir(), `spark_reduced_${Date.now()}.md`);
    const scriptPath = path.join(__dirname, 'scripts', 'reduce_log.py');
    const workspaceRoot = path.resolve(__dirname, '..');

    await runFile('python', [scriptPath, '--zip', zipPath, '--out', outputFile, ...(compact ? ['--compact'] : [])], workspaceRoot);

    const reducedReport = await fs.readFile(outputFile, 'utf-8');
    await fs.unlink(outputFile).catch(() => {});

    return { reducedReport };
  });

  ipcMain.handle('submit-reduced-for-analysis', async (_event, payload) => {
    const apiBaseUrl = (payload && payload.apiBaseUrl) || 'http://localhost:8000';
    const reducedReport = payload && payload.reducedReport;
    const pyFilePaths = (payload && payload.pyFilePaths) || [];
    const llmProvider = payload && payload.llmProvider;
    const apiKey = payload && payload.apiKey;
    const language = (payload && payload.language) || 'en';

    if (!reducedReport || !String(reducedReport).trim()) {
      throw new Error('reducedReport is required');
    }

    const form = new FormData();
    form.append('reduced_report', reducedReport);
    form.append('language', language);
    if (llmProvider) {
      form.append('llm_provider', llmProvider);
    }
    if (apiKey) {
      form.append('api_key', apiKey);
    }

    for (const filePath of pyFilePaths) {
      const fileBuffer = await fs.readFile(filePath);
      const fileName = path.basename(filePath);
      form.append('pyspark_files', new Blob([fileBuffer]), fileName);
    }

    const res = await fetch(`${apiBaseUrl}/api/upload-reduced`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`upload-reduced failed (${res.status}): ${errText}`);
    }

    return res.json();
  });

  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
