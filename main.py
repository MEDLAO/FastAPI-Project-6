from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import uuid
import os


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yassintarjimly.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# Create and serve "filtered" folder
os.makedirs("filtered", exist_ok=True)
app.mount("/filtered", StaticFiles(directory="filtered"), name="filtered")


# === Provided functions ===
def get_transparent_circle_bounds(filter_path):
    filter_img = Image.open(filter_path).convert("RGBA")
    alpha = filter_img.split()[3]  # get alpha channel

    # Get the bounding box of the fully transparent area
    transparent_mask = alpha.point(lambda x: 255 if x == 0 else 0)
    bbox = transparent_mask.getbbox()

    return bbox  # (left, upper, right, lower)


def apply_filter_with_circle(uploaded_path, filter_path, output_path):
    # Load images
    uploaded_img = Image.open(uploaded_path).convert("RGBA")
    filter_img = Image.open(filter_path).convert("RGBA")

    # Define transparent circle bounds
    circle_bounds = get_transparent_circle_bounds(filter_path)
    circle_width = circle_bounds[2] - circle_bounds[0]
    circle_height = circle_bounds[3] - circle_bounds[1]

    # Resize uploaded image to match the circle area
    uploaded_resized = uploaded_img.resize((circle_width, circle_height))

    # Create a transparent canvas
    background = Image.new("RGBA", filter_img.size, (0, 0, 0, 0))

    # Paste uploaded image at the circle location
    background.paste(uploaded_resized, (circle_bounds[0], circle_bounds[1]))

    # Combine with the filter
    final_image = Image.alpha_composite(background, filter_img)

    # Save the final image
    final_image.save(output_path)


def delete_after_delay(path, delay=60):
    import time
    time.sleep(delay)
    if os.path.exists(path):
        os.remove(path)


@app.get("/", response_class=FileResponse)
def serve_index():
    return FileResponse("index.html")


# === Endpoint ===
@app.post("/apply-filter", response_class=HTMLResponse)
async def apply_filter(uploaded_file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    input_path = f"temp_{uuid.uuid4()}.png"
    with open(input_path, "wb") as f:
        f.write(await uploaded_file.read())

    output_filename = f"tarjimly_image_{uuid.uuid4().hex[:8]}.png"
    output_path = f"filtered/{output_filename}"

    apply_filter_with_circle(input_path, "tarjimly_filter.png", output_path)
    background_tasks.add_task(os.remove, input_path)
    background_tasks.add_task(delete_after_delay, output_path, 10)

    # Return HTML with the image and download button
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Tarjimly Image Filter</title>

      <!-- Google Fonts -->
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&family=Roboto+Slab&display=swap" rel="stylesheet">

      <style>
        html, body {{
          margin: 0;
          padding: 0;
          height: 100vh;
          overflow-y: hidden;
        }}

        body {{
          background-color: #ffffff;
          font-family: "Segoe UI", sans-serif;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-start;
          padding-top: 10px;
          padding-bottom: 10px;
          color: #222;
        }}

        a {{
          text-decoration: none;
        }}

        .logo {{
          width: 230px;
          margin-top: 10px;
          margin-bottom: 5px;
          cursor: pointer;
        }}

        h2 {{
          font-family: 'Roboto Slab', serif;
          color: #0A1732;
          font-size: 28px;
          margin-bottom: 5px;
        }}

        p {{
          color: #333;
          margin-bottom: 30px;
          font-size: 16px;
        }}

        form {{
          background: #f9f9f9;
          padding: 30px 40px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
          text-align: center;
          max-width: 400px;
          width: 100%;
        }}

        .frame-preview {{
          margin-bottom: 20px;
        }}

        .frame-preview img {{
          width: 315px;
          border-radius: 8px;
        }}

        .frame-preview small {{
          display: block;
          margin-top: 8px;
          color: #666;
          font-size: 14px;
        }}

        .btn {{
          font-family: 'DM Sans', sans-serif;
          font-weight: 600;
          background-color: #386BB8;
          color: white;
          border: none;
          padding: 12px 28px;
          font-size: 12px;
          border-radius: 4px;
          cursor: pointer;
          transition: background-color 0.3s ease;
        }}

        .btn:hover {{
          background-color: #1E4380;
        }}
      </style>
    </head>
    <body>

      <!-- Clickable Tarjimly Logo -->
      <a href="https://www.tarjimly.org/" target="_blank">
        <img src="/static/tarjimly_logo.png" alt="Tarjimly Logo" class="logo">
      </a>

      <h2>Apply Tarjimly Filter to Your Image</h2>
      <p>Select a photo and download it with the official Tarjimly circular frame</p>

      <form>
          <!-- Filtered Image Preview -->
          <div class="frame-preview">
            <img src="/filtered/{output_filename}" alt="Filtered Image Preview">
            <small>Here’s your image with the Tarjimly frame</small>
          </div>
        
          <!-- Download and Go Back buttons -->
          <div style="display: flex; justify-content: center; gap: 10px;">
            <a href="/">
              <button type="button" class="btn">Go Back to Form</button>
            </a>
            <a href="/filtered/{output_filename}" download>
              <button type="button"  class="btn">Download Image</button>
            </a>
          </div>
      </form>

    </body>
    </html>
    """



