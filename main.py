from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from PIL import Image
from io import BytesIO
import uuid
import os

app = FastAPI()


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


# === API route ===
@app.post("/apply-filter")
async def apply_filter(uploaded_file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    # Save uploaded file temporarily
    input_path = f"temp_{uuid.uuid4()}.png"
    with open(input_path, "wb") as f:
        content = await uploaded_file.read()
        f.write(content)

    # Output path
    output_path = f"result_{uuid.uuid4()}.png"

    # Apply the filter
    apply_filter_with_circle(input_path, "tarjimly_filter.png", output_path)

    # Schedule cleanup after response is sent
    background_tasks.add_task(os.remove, input_path)
    background_tasks.add_task(os.remove, output_path)

    # Return the result image as downloadable file
    return FileResponse(
        output_path,
        media_type="image/png",
        filename="filtered_image.png",
        headers={"Content-Disposition": "attachment; filename=filtered_image.png"}
    )
