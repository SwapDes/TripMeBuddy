import google.generativeai as genai

genai.configure(api_key="AIzaSyDyCGKbtkqVlHVoLeIhk2AGvtzDdaakryA")

# List all available models
models = genai.list_models()

print("Available Models:")
for model in models:
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n{model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Input Token Limit: {model.input_token_limit}")
        print(f"  Output Token Limit: {model.output_token_limit}")
