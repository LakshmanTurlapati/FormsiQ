export const environment = {
  production: true,
  // CloudFront URL - HTTPS access to backend via CloudFront (direct to ECS)
  apiUrl: 'https://d9po4qfa5d50l.cloudfront.net/api',
  // Model availability in production (only Grok available in cloud deployment)
  availableModels: ['grok']
}; 