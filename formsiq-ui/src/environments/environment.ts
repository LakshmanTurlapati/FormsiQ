export const environment = {
  production: false,
  // CloudFront URL - HTTPS access to backend via CloudFront (direct to ECS)
  apiUrl: 'https://d9po4qfa5d50l.cloudfront.net/api',
  // Model availability in development (only Grok available)
  availableModels: ['grok']
}; 