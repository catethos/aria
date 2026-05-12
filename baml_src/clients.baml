client Claude {
  provider "openai-generic"
  options {
    model "anthropic/claude-sonnet-4.6"
    api_key env.OPENROUTER_API_KEY
    base_url "https://openrouter.ai/api/v1"
  }
}
