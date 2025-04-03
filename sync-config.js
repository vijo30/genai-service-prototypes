const fs = require('fs');
const path = require('path');

// Configuración de rutas
const PATHS = {
  shared: {
    case: path.join(__dirname, 'shared', 'caso-sebastian.txt'),
    env: path.join(__dirname, 'shared', '.env.shared')
  },
  backend: {
    config: path.join(__dirname, 'backend', 'config', 'generated_config.py'),
    env: path.join(__dirname, 'backend', '.env')
  },
  frontend: {
    config: path.join(__dirname, 'frontend', 'src', 'shared_config', 'case_config.json'),
    env: path.join(__dirname, 'frontend', '.env')
  }
};

// Función para leer archivos seguros
const readFileSafe = (path) => {
  try {
    return fs.readFileSync(path, 'utf-8');
  } catch (error) {
    console.error(`Error leyendo ${path}:`, error.message);
    return '';
  }
};

// 1. Sincronizar el caso ético
const syncCase = () => {
  const caseContent = readFileSafe(PATHS.shared.case);

  // Backend (Python)
  const backendContent = `# GENERADO AUTOMÁTICAMENTE - NO EDITAR MANUALMENTE\n\n` +
                        `SEBASTIAN_CASE = """\n${caseContent}\n"""`;
  fs.writeFileSync(PATHS.backend.config, backendContent);

  // Frontend (JSON)
  const frontendContent = JSON.stringify({ caso_sebastian: caseContent }, null, 2);
  fs.writeFileSync(PATHS.frontend.config, frontendContent);

  console.log('✅ Caso sincronizado a frontend y backend');
};

// 2. Sincronizar variables de entorno
const syncEnvVars = () => {
  const sharedVars = readFileSafe(PATHS.shared.env);
  
  // Backend - Combinar sin duplicados
  const currentBackendEnv = readFileSafe(PATHS.backend.env);
  const newBackendEnv = currentBackendEnv.split('\n')
    .filter(line => !line.startsWith('#') && line.trim())
    .concat(sharedVars.split('\n'))
    .filter((value, index, self) => self.indexOf(value) === index)
    .join('\n');
  fs.writeFileSync(PATHS.backend.env, newBackendEnv);

  // Frontend - Prefijo REACT_APP_
  const reactVars = sharedVars.split('\n')
    .filter(line => line.trim() && !line.startsWith('#'))
    .map(line => `REACT_APP_${line}`)
    .join('\n');
  fs.writeFileSync(PATHS.frontend.env, reactVars);

  console.log('✅ Variables de entorno sincronizadas');
};

// Ejecutar todo
syncCase();
syncEnvVars();
console.log('🚀 Sincronización completada');