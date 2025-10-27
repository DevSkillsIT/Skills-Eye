// Test if we can parse the exports from api.ts
import * as apiModule from './src/services/api.ts';

console.log('Exported names:', Object.keys(apiModule));
console.log('Has DashboardMetrics:', 'DashboardMetrics' in apiModule);
