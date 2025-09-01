const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const url = require('url');
const isDev = process.env.NODE_ENV === 'development';

let backendProcess = null;
let mainWindow = null;
let frontendServer = null;

// Start the FastAPI backend server
async function startBackend() {
  // First check if backend is already running
  try {
    const response = await fetch('http://127.0.0.1:8000/health');
    if (response.ok) {
      console.log('Backend is already running on port 8000');
      return;
    }
  } catch (error) {
    console.log('No backend found on port 8000, starting new one...');
  }

  const backendPath = isDev ? path.join(__dirname, '../backend') : path.join(process.resourcesPath, 'backend');
  const backendExecutable = isDev ? 'python' : path.join(process.resourcesPath, 'scholar-backend');
  
  console.log('Starting backend server...');
  console.log('Backend path:', backendPath);
  console.log('Backend executable:', backendExecutable);
  
  if (isDev) {
    backendProcess = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
      cwd: backendPath,
      stdio: 'pipe'
    });
  } else {
    // Use system Python with the bundled backend
    const pythonPaths = [
      '/opt/homebrew/bin/python3',
      '/usr/bin/python3',
      '/usr/local/bin/python3',
      'python3',
      'python'
    ];
    
    const backendDir = path.join(process.resourcesPath, 'backend');
    console.log('Backend dir:', backendDir);
    
    // Try to find an available Python executable
    let pythonPath = null;
    for (const path of pythonPaths) {
      try {
        require('child_process').execSync(`which ${path}`, { stdio: 'ignore' });
        pythonPath = path;
        break;
      } catch (e) {
        // Continue to next path
      }
    }
    
    if (!pythonPath) {
      throw new Error('No Python executable found. Please install Python 3.8+');
    }
    
    console.log('Using Python path:', pythonPath);
    
    // Try to start the backend with the bundled version first
    try {
      backendProcess = spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
        cwd: backendDir,
        stdio: 'pipe',
        env: {
          ...process.env,
          PYTHONPATH: backendDir
        }
      });
    } catch (error) {
      console.log('Bundled backend failed, trying system backend...');
      
      // Fallback to system backend if bundled one fails
      const systemBackendDir = path.join(__dirname, '../backend');
      if (require('fs').existsSync(systemBackendDir)) {
        backendProcess = spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
          cwd: systemBackendDir,
          stdio: 'pipe',
          env: {
            ...process.env,
            PYTHONPATH: systemBackendDir
          }
        });
      } else {
        throw new Error('Neither bundled nor system backend found');
      }
    }
  }

  backendProcess.stdout.on('data', (data) => {
    console.log('Backend stdout:', data.toString());
  });

  backendProcess.stderr.on('data', (data) => {
    console.log('Backend stderr:', data.toString());
  });

  backendProcess.on('close', (code) => {
    console.log('Backend process exited with code:', code);
  });

  backendProcess.on('error', (error) => {
    console.error('Backend process error:', error);
  });

  // Wait a bit for backend to start and verify it's working
  return new Promise((resolve, reject) => {
    const checkBackend = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/health');
        if (response.ok) {
          console.log('Backend is now running and responding');
          resolve();
        } else {
          reject(new Error('Backend started but health check failed'));
        }
      } catch (error) {
        reject(new Error('Backend failed to start: ' + error.message));
      }
    };
    
    setTimeout(checkBackend, 3000);
  });
}

// Stop the backend server
function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend server...');
    backendProcess.kill();
    backendProcess = null;
  }
}

function createWindow() {
  console.log('Creating main window...');
  
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: false, // Allow local file access and API calls
      allowRunningInsecureContent: true, // Allow HTTP requests from file://
    },
    icon: path.join(__dirname, 'assets/scholarlogo.png'), // Icon for all platforms
    show: false, // Don't show until ready
  });

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    console.log('Window ready to show');
    mainWindow.show();
  });

  // Load the app
  if (isDev) {
    console.log('Loading from development server: http://localhost:3000');
    // In development, load from Next.js dev server
    mainWindow.loadURL('http://localhost:3000');
    // DevTools can be opened manually with Cmd+Option+I (Mac) or Ctrl+Shift+I (Windows/Linux)
  } else {
    // In production, load from our local HTTP server
    console.log('Loading from local HTTP server: http://127.0.0.1:3001');
    mainWindow.loadURL('http://127.0.0.1:3001');
  }

  // Handle window closed
  mainWindow.on('closed', () => {
    // Dereference the window object
    mainWindow = null;
  });
}

// Start a simple HTTP server to serve frontend files
function startFrontendServer() {
  const frontendDir = isDev ? path.join(__dirname, '../frontend/out') : path.join(process.resourcesPath, 'frontend');
  const port = 3001;
  
  console.log('Starting frontend server on port', port);
  console.log('Frontend directory:', frontendDir);
  console.log('Directory exists:', fs.existsSync(frontendDir));
  
  if (!fs.existsSync(frontendDir)) {
    console.error('Frontend directory not found:', frontendDir);
    throw new Error(`Frontend directory not found: ${frontendDir}`);
  }
  
  // List contents of frontend directory
  try {
    const files = fs.readdirSync(frontendDir);
    console.log('Frontend directory contents:', files);
  } catch (error) {
    console.error('Error reading frontend directory:', error);
  }
  
  frontendServer = http.createServer((req, res) => {
    let filePath = url.parse(req.url).pathname;
    
    console.log('Request for:', filePath);
    
    // Default to index.html for root
    if (filePath === '/') {
      filePath = '/index.html';
    }
    
    // Remove leading slash
    filePath = filePath.substring(1);
    
    // Security: prevent directory traversal
    if (filePath.includes('..')) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }
    
    const fullPath = path.join(frontendDir, filePath);
    console.log('Full path:', fullPath);
    
    // Check if file exists
    if (!fs.existsSync(fullPath)) {
      console.error('File not found:', fullPath);
      res.writeHead(404);
      res.end(`File not found: ${filePath}`);
      return;
    }
    
    // Check if it's a directory - if so, try to serve index.html from that directory
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      const indexPath = path.join(fullPath, 'index.html');
      if (fs.existsSync(indexPath)) {
        console.log('Directory requested, serving index.html from:', indexPath);
        serveFile(indexPath, res);
        return;
      } else {
        console.error('Directory requested but no index.html found:', fullPath);
        res.writeHead(404);
        res.end(`Directory requested but no index.html found: ${filePath}`);
        return;
      }
    }
    
    // It's a file, serve it
    serveFile(fullPath, res);
  });
  
  // Helper function to serve a file
  function serveFile(filePath, res) {
    // Get file extension for content type
    const ext = path.extname(filePath);
    const contentType = {
      '.html': 'text/html',
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.json': 'application/json',
      '.png': 'image/png',
      '.jpg': 'image/jpg',
      '.gif': 'image/gif',
      '.svg': 'image/svg+xml',
      '.woff': 'font/woff',
      '.woff2': 'font/woff2',
      '.ttf': 'font/ttf',
      '.eot': 'application/vnd.ms-fontobject'
    }[ext] || 'application/octet-stream';
    
    // Read and serve file
    fs.readFile(filePath, (err, data) => {
      if (err) {
        console.error('Error reading file:', filePath, err);
        res.writeHead(500);
        res.end(`Error loading file: ${err.message}`);
        return;
      }
      
      console.log('Serving file:', filePath, 'Content-Type:', contentType);
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    });
  }
  
  frontendServer.listen(port, '127.0.0.1', () => {
    console.log(`Frontend server running on http://127.0.0.1:${port}`);
  });
  
  return new Promise((resolve) => {
    setTimeout(resolve, 1000);
  });
}

// Stop the frontend server
function stopFrontendServer() {
  if (frontendServer) {
    console.log('Stopping frontend server...');
    frontendServer.close();
    frontendServer = null;
  }
}

// Log app structure for debugging
function logAppStructure() {
  console.log('=== App Structure Debug ===');
  console.log('__dirname:', __dirname);
  console.log('process.resourcesPath:', process.resourcesPath);
  console.log('process.execPath:', process.execPath);
  
  try {
    const fs = require('fs');
    console.log('Files in __dirname:');
    try {
      const files = fs.readdirSync(__dirname);
      console.log(files);
    } catch (e) {
      console.log('Cannot read __dirname:', e.message);
    }
    
    if (process.resourcesPath) {
      console.log('Files in resourcesPath:');
      try {
        const resourceFiles = fs.readdirSync(process.resourcesPath);
        console.log(resourceFiles);
      } catch (e) {
        console.log('Cannot read resourcesPath:', e.message);
      }
    }
  } catch (error) {
    console.log('Error reading file system:', error.message);
  }
  console.log('==========================');
}

// This method will be called when Electron has finished initialization
app.whenReady().then(async () => {
  console.log('Electron app is ready, starting backend...');
  
  // Log app structure for debugging
  logAppStructure();
  
  try {
    // Start backend first
    await startBackend();
    console.log('Backend started successfully');
    
    // Start frontend server
    await startFrontendServer();
    console.log('Frontend server started successfully');
    
    // Then create window
    createWindow();
    console.log('Main window created');
  } catch (error) {
    console.error('Error during startup:', error);
    app.quit();
  }

  // On macOS, re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  stopBackend();
  stopFrontendServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Clean up backend when app quits
app.on('before-quit', () => {
  stopBackend();
  stopFrontendServer();
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
  });
});
