import ffmpeg
import logging
import sys
import os
import tempfile
from io import BytesIO
from django.conf import settings

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seaer_ai.seaer_cwt_overlay import seaer_cwt_overlay  # Import the function directly

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FFmpeg parameters
input_stream = sys.argv[1] if len(sys.argv) > 1 else "rtsp://your_rtsp_url"
output_stream = f"{sys.argv[2]}/{sys.argv[3]}" if len(sys.argv) > 3 else "rtmp://your_youtube_stream_url"

location1 = sys.argv[4] if len(sys.argv) > 4 else "Shrewsberry River"
location2 = sys.argv[5] if len(sys.argv) > 5 else "Monmouth Beach NJ"
stationName = sys.argv[6] if len(sys.argv) > 6 else "8531942"

overlay_image = seaer_cwt_overlay(location1, location2, stationName)

if isinstance(overlay_image, BytesIO):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file.write(overlay_image.getvalue())
    temp_file.close()
    overlay_image_path = temp_file.name
else:
    overlay_image_path = overlay_image

def run_ffmpeg():
    try:
        video_input = ffmpeg.input(input_stream, thread_queue_size=2048, rtsp_transport='tcp')
        audio_input = ffmpeg.input('anullsrc', f='lavfi')
        overlay_input = ffmpeg.input(overlay_image_path)
        
        overlay_output = ffmpeg.overlay(video_input, overlay_input, x=100, y=800)
        
        (
            ffmpeg
            .output(overlay_output, audio_input, output_stream, acodec='aac', vcodec='libx264', f='flv')
            .run()
        )
        logging.info("FFmpeg process completed successfully")
    except ffmpeg.Error as e:
        logging.error("FFmpeg error occurred: " + str(e))
    except Exception as e:
        logging.error("An error occurred: " + str(e))
    finally:
        if isinstance(overlay_image, BytesIO):
            os.remove(overlay_image_path)

def capture_stream_image():
    try:
        video_input = ffmpeg.input(input_stream, thread_queue_size=2048, rtsp_transport='tcp')
        overlay_input = ffmpeg.input(overlay_image_path)
        
        overlay_output = ffmpeg.overlay(video_input, overlay_input, x=100, y=800)
        
        # Save the image to the static directory
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'captured_images')
        os.makedirs(static_dir, exist_ok=True)
        image_filename = "captured_image.png"
        image_path = os.path.join(static_dir, image_filename)
        
        (
            ffmpeg
            .output(overlay_output, image_path, vframes=1)
            .overwrite_output()  # This adds the -y option to overwrite the output file
            .global_args('-update', '1')  # This adds the -update 1 option
            .run()
        )
        logging.info("Stream image captured successfully")
        print(image_filename)  # Print only the filename
    except ffmpeg.Error as e:
        logging.error("FFmpeg error occurred: " + str(e))
    except Exception as e:
        logging.error("An error occurred: " + str(e))
    finally:
        if isinstance(overlay_image, BytesIO):
            os.remove(overlay_image_path)

if __name__ == "__main__":
    if '--capture-image' in sys.argv:
        capture_stream_image()
    else:
        run_ffmpeg()
