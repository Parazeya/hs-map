import { mount } from 'svelte';

import '../theme.css';
import Codex from './Codex.svelte';

export default mount(Codex, { target: document.getElementById('app') });
