import requests
import time

def test_pipeline():
    file_path = r"c:\Users\91999\Desktop\faq\sample_5_page_test.pdf"
    
    # 1. Ingest
    print("--- Step 1: Ingesting PDF ---")
    start_time = time.time()
    with open(file_path, 'rb') as f:
        response = requests.post("http://127.0.0.1:8000/ingest/document", files={"file": f})
    
    if response.status_code != 200:
        print(f"Ingest failed: {response.text}")
        return
    
    source_id = response.json()["source_id"]
    print(f"Ingested successfully. ID: {source_id} (Time: {time.time() - start_time:.2f}s)")

    # 2. Generate
    print("\n--- Step 2: Triggering FAQ Generation ---")
    start_time = time.time()
    response = requests.post(f"http://127.0.0.1:8000/generate/faq?source_id={source_id}&num_faqs=5")
    
    if response.status_code != 200:
        print(f"Generation trigger failed: {response.text}")
        return
    
    task_id = response.json()["task_id"]
    print(f"Task started. ID: {task_id}")

    # 3. Poll for results
    print("\n--- Step 3: Polling for Results ---")
    while True:
        response = requests.get(f"http://127.0.0.1:8000/results/{task_id}")
        data = response.json()
        status = data["status"]
        print(f"Status: {status}...")
        
        if status == "completed":
            total_time = time.time() - start_time
            print(f"\nSUCCESS! Generated {len(data['result'])} FAQs.")
            print(f"Total Generation Time: {total_time:.2f} seconds")
            break
        elif status == "failed":
            print(f"\nFAILED: {data['result']['error']}")
            break
        
        time.sleep(3)

if __name__ == "__main__":
    test_pipeline()
