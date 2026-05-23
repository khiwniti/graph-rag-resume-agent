import requests

NVIDIA_API_KEY = "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"

def analyze_resume_with_nvidia(resume_text):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-4-340b-instruct",
        "messages": [{"role": "user", "content": resume_text}],
        "max_tokens": 64
    }
    response = requests.post(url, headers=headers, json=payload)
    return response

if __name__ == "__main__":
    test_resume = "John Doe is a software engineer with 5 years of experience in Python and JavaScript."
    r = analyze_resume_with_nvidia(test_resume)
    print("Status code:", r.status_code)
    try:
        print("JSON response:", r.json())
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Response text:", r.text)
