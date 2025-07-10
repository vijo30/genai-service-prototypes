const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

console.log('🚀 Iniciando script de sincronización de configuraciones...');

// --- CONFIGURACIÓN DE RUTAS ---
const BASE_DIR = __dirname;
const PATHS = {
  shared: {
    case: path.join(BASE_DIR, 'shared', 'caso-sebastian.txt'),
    publicEnv: path.join(BASE_DIR, 'shared', '.env.public'), // Archivo para variables públicas
    privateEnv: path.join(BASE_DIR, 'shared', '.env.private') // Archivo para secretos
  },
  backend: {
    configDir: path.join(BASE_DIR, 'backend', 'config'),
    configFile: path.join(BASE_DIR, 'backend', 'config', 'generated_config.py'),
    envFile: path.join(BASE_DIR, 'backend', '.env')
  },
  frontend: {
    configDir: path.join(BASE_DIR, 'frontend', 'src', 'shared_config'),
    configFile: path.join(BASE_DIR, 'frontend', 'src', 'shared_config', 'case_config.json'),
    envFile: path.join(BASE_DIR, 'frontend', '.env')
  }
};

// --- FUNCIONES AUXILIARES (más robustas) ---

const readFileSafe = (filePath) => (fs.existsSync(filePath) ? fs.readFileSync(filePath, 'utf-8') : '');
const parseEnvFile = (filePath) => (fs.existsSync(filePath) ? dotenv.parse(Buffer.from(readFileSafe(filePath))) : {});

const writeFileSafe = (filePath, content) => {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filePath, content, 'utf-8');
};

const writeEnvFile = (filePath, envObject) => {
  const content = Object.entries(envObject).map(([key, value]) => `${key}=${value}`).join('\n');
  writeFileSafe(filePath, content);
};

// --- LÓGICA DE SINCRONIZACIÓN ---

const syncCaseFile = () => {
  console.log('🔄 Sincronizando caso de estudio...');
  const caseContent = readFileSafe(PATHS.shared.case);
  if (!caseContent) {
    console.warn('⚠️  El archivo del caso está vacío o no se pudo leer.');
    return;
  }
  const backendContent = `# GENERADO AUTOMÁTICAMENTE\n\nSEBASTIAN_CASE = """${caseContent.replace(/"/g, '\\"')}"""`;
  writeFileSafe(PATHS.backend.configFile, backendContent);
  const frontendContent = JSON.stringify({ caso_sebastian: caseContent }, null, 2);
  writeFileSafe(PATHS.frontend.configFile, frontendContent);
  console.log('✅ Caso de estudio sincronizado.');
};

const syncEnvVars = () => {
  console.log('🔄 Sincronizando variables de entorno...');
  const publicVars = parseEnvFile(PATHS.shared.publicEnv);
  const privateVars = parseEnvFile(PATHS.shared.privateEnv);

  // --- Sincronización del Backend (recibe TODO) ---
  const currentBackendVars = parseEnvFile(PATHS.backend.envFile);
  const finalBackendVars = { ...currentBackendVars, ...publicVars, ...privateVars };
  writeEnvFile(PATHS.backend.envFile, finalBackendVars);
  console.log('✅ Variables de entorno del backend actualizadas (públicas y privadas).');

  // --- Sincronización del Frontend (recibe SÓLO lo público) ---
  const currentFrontendVars = parseEnvFile(PATHS.frontend.envFile);
  const reactPublicVars = {};
  for (const key in publicVars) {
    reactPublicVars[`REACT_APP_${key}`] = publicVars[key];
  }
  // Se mantienen las variables que ya existen y no entran en conflicto con las públicas
  const finalFrontendVars = { ...currentFrontendVars, ...reactPublicVars };
  writeEnvFile(PATHS.frontend.envFile, finalFrontendVars);
  console.log('✅ Variables de entorno del frontend actualizadas (solo públicas).');
};

// --- EJECUCIÓN PRINCIPAL ---
try {
  syncCaseFile();
  syncEnvVars();
  console.log('\n✨ Sincronización completada con éxito.');
} catch (error) {
  console.error('\n❌ Ha ocurrido un error durante la sincronización:', error);
  process.exit(1);
}