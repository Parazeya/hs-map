import { mount } from 'svelte';

import '../theme.css';
import Skills from './Skills.svelte';

export default mount(Skills, { target: document.getElementById('app') });
