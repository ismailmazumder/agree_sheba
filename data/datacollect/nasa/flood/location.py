from geopy.geocoders import Nominatim

# Initialize Nominatim geolocator (requires a unique user_agent to identify your app)
geolocator = Nominatim(user_agent="my_geocoder_app_v1")

# Define the place name or address
place_name = "Eidgaon, Cox'sbazar"

# Fetch location details
location = geolocator.geocode(place_name)

# Extract latitude and longitude
if location:
    print(f"Place: {location.address}")
    print(f"Latitude: {location.latitude}")
    print(f"Longitude: {location.longitude}")
else:
    print("No results found for that place name.")