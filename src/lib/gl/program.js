// Shader compilation with an error message worth reading.
//
// A driver reports `ERROR: 0:37: '' : syntax error` and nothing else. On its own
// that is close to useless in a browser console — line 37 of which of six
// shaders? So a failure here carries the program's name, the driver's log, and
// the numbered source lines around the one it blamed.

/** `ERROR: 0:37: …` → 37, or null when the log does not name a line */
function blamedLine(log) {
  const m = /^[^\n]*?\b\d+:(\d+):/m.exec(log ?? '');
  return m ? Number(m[1]) : null;
}

/** the source around `line`, numbered, so the driver's complaint has context */
function excerpt(src, line, span = 3) {
  const lines = src.split('\n');
  if (line == null) return '';
  const from = Math.max(0, line - span - 1);
  const to = Math.min(lines.length, line + span);
  return lines
    .slice(from, to)
    .map((t, i) => `${from + i + 1 === line ? '>' : ' '} ${String(from + i + 1).padStart(4)} | ${t}`)
    .join('\n');
}

function compile(gl, type, src, name, kind) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (gl.getShaderParameter(sh, gl.COMPILE_STATUS)) return sh;
  const log = gl.getShaderInfoLog(sh) ?? '(no log)';
  gl.deleteShader(sh);
  const ctx = excerpt(src, blamedLine(log));
  throw new Error(`${name} ${kind} shader failed to compile:\n${log.trim()}${ctx ? `\n${ctx}` : ''}`);
}

/**
 * Compile + link one program and hand back a small handle.
 * `u(name)` caches uniform locations: getUniformLocation is a round trip to the
 * driver, and a frame asks for the same handful over and over.
 *
 * @returns {{ program: WebGLProgram, u: (name: string) => WebGLUniformLocation | null, free: () => void }}
 */
export function createProgram(gl, vert, frag, name = 'program') {
  const program = gl.createProgram();
  const vs = compile(gl, gl.VERTEX_SHADER, vert, name, 'vertex');
  let fs;
  try {
    fs = compile(gl, gl.FRAGMENT_SHADER, frag, name, 'fragment');
  } catch (e) {
    gl.deleteShader(vs);
    gl.deleteProgram(program);
    throw e;
  }
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs); // the program keeps what it needs; the objects are done
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program) ?? '(no log)';
    gl.deleteProgram(program);
    throw new Error(`${name} failed to link:\n${log.trim()}`);
  }
  const locs = new Map();
  return {
    program,
    u(uname) {
      if (!locs.has(uname)) locs.set(uname, gl.getUniformLocation(program, uname));
      return locs.get(uname);
    },
    free() {
      locs.clear();
      gl.deleteProgram(program);
    },
  };
}
