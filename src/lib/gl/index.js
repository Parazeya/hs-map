// A small WebGL 2 core for the world map: context, one sprite program, quad
// batching, packed sheets sampled NEAREST, the view, and CPU picking.
//
// Ported from PoETools' src/lib/gl/, which was written for the same problem on
// the passive tree. What was taken, what was left and why is written at the top
// of each file; the short version is that this map has no strokes and no
// circles, so of the tree's three programs it needs one, and it has nothing but
// pixel art, so where the tree builds mip chains this samples NEAREST and
// builds none.
//
// Deliberately free of anything that knows what a marker, a link or a torch is
// — those live in the component on top. Draw ORDER is a component's business
// too: this exposes "draw these batches now" and never decides what comes first.

export { createContext, hasWebGL2, sizeCanvas } from './context.js';
export { Renderer, rgb } from './renderer.js';
export { buildQuads, createDynamicQuads, cellUV, stripUV, freeObject } from './geometry.js';
export { createTexture, packSheet, loadImage, loadAll, freeTexture } from './textures.js';
export { createTarget, freeTarget } from './target.js';
export { View, pointerPos, pickBox } from './view.js';

// createProgram and the two shader strings are not re-exported: renderer.js is
// the only thing that compiles a program, and a component that reached past it
// would be writing a second renderer.
