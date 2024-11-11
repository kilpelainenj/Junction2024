from django.shortcuts import render
from .forms import UploadFileForm
import requests
import base64
import time
from django.http import HttpResponse
import ifcopenshell

from django.core.cache import cache
from .models import IfcFile

from dotenv import load_dotenv
import os
import random

load_dotenv()

# Import the processing functions
from calculating.geometry import (
    filter_furnishment,
    filter_low_volume_elements,
    beam_and_columns,
    find_vertices_and_intersections,
    mark_vertices,
)
from calculating.SteelOrConcrete import material_identifier 

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

def get_forge_access_token():
    token = cache.get('forge_access_token')
    if token:
        return token
    else:
        url = 'https://developer.api.autodesk.com/authentication/v2/token'
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
            'scope': 'data:read data:write data:create bucket:create bucket:read'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            token = response.json()['access_token']
            expires_in = response.json()['expires_in']
            cache.set('forge_access_token', token, timeout=expires_in)
            return token
        else:
            return None

def create_bucket(access_token, bucket_name):
    url = 'https://developer.api.autodesk.com/oss/v2/buckets'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'bucketKey': bucket_name,
        'policyKey': 'transient'
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in (200, 409):
        return True
    else:
        return False

def upload_ifc_file(access_token, bucket_name, object_name, file_content):
    upload_url = f'https://developer.api.autodesk.com/oss/v2/buckets/{bucket_name}/objects/{object_name}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }
    response = requests.put(upload_url, headers=headers, data=file_content)
    if response.status_code in (200, 201):
        object_id = response.json()['objectId']
        return object_id
    else:
        
        print(f"Upload failed with status code {response.status_code}: {response.text}")
        return None

def translate_ifc_file(access_token, urn):
    translate_url = 'https://developer.api.autodesk.com/modelderivative/v2/designdata/job'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "input": {
            "urn": urn
        },
        "output": {
            "formats": [
                {
                    "type": "svf",
                    "views": ["3d"]
                }
            ]
        }
    }
    response = requests.post(translate_url, headers=headers, json=data)
    if response.status_code in (200, 201):
        return True
    else:
        return False

def check_translation_status(access_token, urn):
    status_url = f'https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/manifest'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(status_url, headers=headers)
    if response.status_code == 200:
        response_json = response.json()
        status = response_json.get('status')
        if status == 'success':
            return True
        elif status in ['inprogress', 'pending']:
            return False
        else:
            # Log unexpected statuses
            print(f"Translation status is '{status}': {response.text}")
            return None
    else:
        # Log the error details
        print(f"Status check failed with status code {response.status_code}: {response.text}")
        return None

def home(request):
    form = UploadFileForm()
    urn = None
    access_token = None  # Initialize access_token
    total_intersections = 0
    intersection_counts = {}
    estimated_cost = None

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            new_ifc = IfcFile.objects.create(ifc_file=file)
            new_ifc.save()

            # Process the IFC file
            file_path = new_ifc.ifc_file.path

            try:
                
                model = ifcopenshell.open(file_path)

                # Apply your processing steps
                filter_furnishment(model)
                filter_low_volume_elements(model, volume_threshold=0.01)
                beams, columns = beam_and_columns(model)

                # Get vertices to mark and element pairs
                vertices_to_mark, element_pairs = find_vertices_and_intersections(beams, columns, distance=1, distance_too_close=0.1)
                # Overwrite the original IFC file with the modified model
                mark_vertices(model, vertices_to_mark, file_path)

                # Initialize counts
                intersection_counts = {
                    'concrete_to_concrete': 0,
                    'steel_to_concrete': 0,
                    'concrete_to_steel': 0,
                    'steel_to_steel': 0,
                    'other': 0,
                }

                total_intersections = len(element_pairs)

                estimated_cost = random.randint(total_intersections * 90, total_intersections * 140)


                for id1, id2 in element_pairs:
                    mat1, mat2 = material_identifier(id1, id2, model)
                    if mat1 == 'concrete' and mat2 == 'concrete':
                        intersection_counts['concrete_to_concrete'] += 1
                    elif mat1 == 'steel' and mat2 == 'concrete':
                        intersection_counts['steel_to_concrete'] += 1
                    elif mat1 == 'concrete' and mat2 == 'steel':
                        intersection_counts['concrete_to_steel'] += 1
                    elif mat1 == 'steel' and mat2 == 'steel':
                        intersection_counts['steel_to_steel'] += 1
                    else:
                        intersection_counts['other'] += 1

            except Exception as e:
                return HttpResponse(f'Error processing IFC file: {e}', status=500)

            # Generate Autodesk Forge access token
            access_token = get_forge_access_token()
            if not access_token:
                return HttpResponse('Failed to get access token', status=500)

            # Define bucket and object name
            bucket_name = 'hiisivision-ifc-bucket-12345'  # must be unique across Autodesk Forge
            object_name = os.path.basename(file_path)

            # Create bucket if it doesn't exist
            if not create_bucket(access_token, bucket_name):
                return HttpResponse('Failed to create bucket', status=500)

            # Upload the modified IFC file
            with open(file_path, 'rb') as f:
                file_content = f.read()

            object_id = upload_ifc_file(access_token, bucket_name, object_name, file_content)

            if not object_id:
                return HttpResponse('Failed to upload IFC file', status=500)

            # Encode the URN for Forge Viewer
            urn = base64.urlsafe_b64encode(object_id.encode('utf-8')).decode('utf-8').rstrip('=')

            # Request translation
            if not translate_ifc_file(access_token, urn):
                return HttpResponse('Failed to start translation', status=500)

            # Poll for translation completion
            for _ in range(600):  # Poll time limiter
                time.sleep(5)
                translation_status = check_translation_status(access_token, urn)
                if translation_status is True:
                    break
                elif translation_status is None:
                    return HttpResponse('Translation failed', status=500)
            else:
                return HttpResponse('Translation timed out', status=500)

            # Prepare context data
            context = {
                "form": form,
                "access_token": access_token,
                "urn": urn,
                "current_year": time.strftime("%Y"),
                "total_intersections": total_intersections,
                "intersection_counts": intersection_counts,
                "estimated_cost": estimated_cost,  
            }
            return render(request, "home.html", context)

    # For GET requests or invalid form submissions
    context = {
        "form": form,
        "current_year": time.strftime("%Y"),
        
    }   

    return render(request, "home.html", context)