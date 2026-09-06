import { mount } from 'svelte';

import '../theme.css';
import Bounty from './Bounty.svelte';

export default mount(Bounty, { target: document.getElementById('app') });
