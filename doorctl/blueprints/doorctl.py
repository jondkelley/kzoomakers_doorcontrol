# Filename    : makersweb.py
# Author      : Jon Kelley <jon.kelley@kzoomakers.org>
# Description : Kzoomakers Door Controller
import requests
from flask import Flask, render_template, request, flash, Blueprint, redirect, url_for, current_app
import json
import datetime  # Import the datetime module
from doorctl.sharedlib.get_config import parse_uhppoted_config
import time
from dateutil import tz

from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

HEADERS = {'accept': 'application/json'}

doorctl = Blueprint('doorctl', __name__)

@doorctl.before_request
def run_on_all_routes():
    """
    Used to block requests that aren't from a specific server with the known values
    """
    # Require x-forwarded-for header to serve requests
    if current_app.config['ENABLE_PROXY_DETECTION'] == 'true':
        if 'X-Forwarded-For' not in request.headers:
            return 'Must be behind a proxy'
    # Require x-doorcontrol-security-key header with proper value
    if current_app.config['ENABLE_PROXIED_SECURIY_KEY']:
        header = request.headers.get('x-doorcontrol-security-key', None)
        if header:
            if not header == current_app.config['ENABLE_PROXIED_SECURIY_KEY']:
                return 'Invalid key for header x-doorcontrol-security-key'
        else:
            return 'Missing header x-doorcontrol-security-key'

@doorctl.route('/robots.txt')
@doorctl.route('/<path:subpath>/robots.txt')
def generate_robots_txt():
    robots_txt_content = "User-agent: *\nDisallow: /"
    return Response(robots_txt_content, content_type="text/plain")


@doorctl.route('/', methods=['GET'])
def index():
    return 'It works!'

### config editor ###
@doorctl.route('/accesscontrol/configedit')
def config_edit():
    with open('/etc/uhppoted/uhppoted.conf', 'r') as file:
        content = file.read()
    return render_template('configedit.html', content=content)

@doorctl.route('/accesscontrol/configedit/save', methods=['POST'])
def config_save():
    content = request.form.get('content')
    with open('/etc/uhppoted/uhppoted.conf', 'w') as file:
        file.write(content)
    #flash("File saved successfully!")
    return redirect('/accesscontrol/configedit')

##### controller routes #####

@doorctl.route('/accesscontrol', methods=['GET'])
@doorctl.route('/accesscontrol/', methods=['GET'])
def accesscontrol():
    return render_template('splash.html')


@doorctl.route('/accesscontrol/controller', methods=['GET'])
@doorctl.route('/accesscontrol/controller/', methods=['GET'])
def controllers_list():
    # Fetch the device time from the API
    url = f"{current_app.config['REST_ENDPOINT']}/device"
    response = requests.get(url, headers=HEADERS)

    api_config = parse_uhppoted_config('/etc/uhppoted/uhppoted.conf')
    print(api_config)
    if response.status_code == 200:
        data = response.json()
        for device in data['devices']:
            device_id = device['device-id']

            # Check if the device_id exists in 'api_config'
            if str(device_id) in api_config['devices']:
                # If it exists, update the device information in 'data'
                device_info = api_config['devices'][str(device_id)]
                device.update(device_info)
        print(data)
        return render_template('controllers.html', devices=data.get('devices', []))


##### door stuff #####

@doorctl.route('/accesscontrol/controller/<int:controller_id>/door/<int:door>/swipe', methods=['POST'])
def swipe_card(controller_id, door):
    card_number = request.json.get('card-number')
    try:
        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/door/{door}/swipes"
        response = requests.post(url, json={"card-number": int(card_number)})
        if response.status_code in [401, 404, 405, 500]:
            error_data = response.json()
            # Flashing the error for the JS to pick up
            #flash(error_data.get('message'), 'error')
            return json.dumps({"error": "API error", "message": error_data.get('message')}), 500
        return json.dumps(response.json())
    except requests.RequestException as e:
            return json.dumps({"error": "API error"}), 500
    except Exception as e:
            return json.dumps({"error": "Unknown error", "message": f"{e}"}), 500

@doorctl.route('/accesscontrol/controller/<int:controller_id>/door/<int:door>/delay', methods=['PUT'])
def set_door_delay(controller_id, door):
    delay_time = request.json.get('delay')
    try:
        payload = {"delay": int(delay_time)}

        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/door/{door}/delay"
        response = requests.put(url, json=payload)
        #response = requests.put(REMOTE_API_DELAY_URL.format(device_id, door), json={"delay": delay_time})
        response.raise_for_status()
        return json.dumps(response.json())
    except requests.RequestException as e:
        # Flashing the error for the JS to pick up
        #flash(str(e), 'error')
        return json.dumps({"error": f"API error, {e}"}), 500

@doorctl.route('/accesscontrol/controller/<int:controller_id>/door/<int:door>/state', methods=['PUT'])
def set_door_control(controller_id, door):
    control_state = request.json.get('control')
    try:
        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/door/{door}/control"
        response = requests.put(url, json={"control": control_state})
        response.raise_for_status()
        return json.dumps(response.json())
    except requests.RequestException as e:
        # Flashing the error for the JS to pick up
        #flash(str(e), 'error')
        return json.dumps({"error": f"API error, {e}"}), 500


@doorctl.route('/accesscontrol/controller/<int:controller_id>/doors')
def manage_doors(controller_id):

    # Fetch device status
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/status"
    response = requests.get(url)
    if response.status_code == 200:
        device_status = response.json()
    else:
        device_status = {}
        flash(f"Failed to retrieve device status. Status code: {response.status_code}", "danger")

    # Fetch door details for each door
    door_info = {}
    for door_id in device_status.get('status', {}).get('door-states', {}):
        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/door/{door_id}"
        response = requests.get(url)
        if response.status_code == 200:
            door_info[door_id] = response.json().get('door', {})
        else:
            flash(f"Failed to retrieve door {door_id} details. Status code: {response.status_code}", "danger")

    return render_template('doors.html', controller_id=controller_id, device_status=device_status, door_info=door_info)

##### device info #####
@doorctl.route('/accesscontrol/controller/<int:controller_id>/info')
def display_device_info(controller_id):
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/status"
    response = requests.get(url)
    if response.status_code == 200:
        device_status = response.json()
    else:
        device_status = {}
        flash(f"Failed to retrieve device status. Status code: {response.status_code}", "danger")
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}"
    response = requests.get(url)
    if response.status_code == 200:
        device_info = response.json()
    else:
        device_info = {}
        flash(f"Failed to retrieve device status. Status code: {response.status_code}", "danger")
    return render_template('controller_info.html', controller_id=controller_id, device_status=device_status, device_info=device_info)


##### events #####
def get_events(device_id):
    # Get range of events
    url = f"{current_app.config['REST_ENDPOINT']}/device/{device_id}/events/1000"
    response = requests.get(url, headers={'accept': 'application/json'})
    response_data = response.json()

    first_event = response_data['events']['first']
    last_event = response_data['events']['last']

    events = []

    # Fetch each event starting from the latest and add to the events list
    for i in range(last_event, first_event-1, -1):
        url = f"{current_app.config['REST_ENDPOINT']}/device/{device_id}/event/{i}"
        response = requests.get(url, headers={'accept': 'application/json'})
        event_data = response.json()

        event_dict = {
            "device-id": event_data["event"]["device-id"],
            "event-id": event_data["event"]["event-id"],
            "event-type": event_data["event"]["event-type"],
            "access-granted": event_data["event"]["access-granted"],
            "door-id": event_data["event"]["door-id"],
            "direction": event_data["event"]["direction"],
            "card-number": event_data["event"]["card-number"],
            "timestamp": event_data["event"]["timestamp"],
            "event-reason": event_data["event"]["event-reason"]
        }

        events.append(event_dict)

    return {"events": events}

@doorctl.route('/accesscontrol/controller/<int:controller_id>/events')
def device_events(controller_id):
    event_data = get_events(device_id=controller_id)
    return render_template('events.html', events=event_data, controller_id=controller_id)


##### time profiles #####
@doorctl.route("/accesscontrol/controller//<int:controller_id>/add_time_profile", methods=["GET", "POST"])
def add_time_profile(controller_id):
    if request.method == "POST":
        # Handle form submission for creating a new time profile
        time_profile_id = request.form.get("time_profile_id")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        weekdays = request.form.get("weekdays")
        segment_start = request.form.get("segment_start")
        segment_end = request.form.get("segment_end")

        # Create a dictionary with the time profile data
        time_profile_data = {
            "id": int(time_profile_id),  # Include the time profile ID
            "start-date": start_date,
            "end-date": end_date,
            "weekdays": weekdays,
        }
        time_profile_data['segments'] = [{"start": segment_start, "end": segment_end}]
        # additional_segments = [
        #     {"start": "00:00", "end": "00:00"},
        #     {"start": "00:00", "end": "00:00"}
        # ]
        # time_profile_data['segments'].extend(additional_segments)
        import json
        print(json.dumps(time_profile_data, indent=3))
        # Make a POST request to create the time profile

        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time-profile/{time_profile_id}"
        response = requests.put(
            url, json=time_profile_data
        )
        if response.status_code == 200:
            flash("Time profile created successfully.", "success")
            return redirect(url_for("doorctl.get_time_profiles", controller_id=controller_id))
        else:
            flash("Failed to create time profile. Please check your input and try again.", "danger")

    return render_template("add_time_profile.html", controller_id=controller_id)

@doorctl.route("/accesscontrol/controller/<int:controller_id>/time_profiles", methods=["GET"])
def get_time_profiles(controller_id):
    # Make a GET request to retrieve the list of time profiles for the device
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time-profiles"
    response = requests.get(url)

    if response.status_code == 200:
        time_profiles_data = response.json()
        print(time_profiles_data)
        return render_template("get_time_profiles.html", controller_id=controller_id, time_profiles=time_profiles_data)
    else:
        flash(f"Failed to retrieve time profiles. Status code: {response.status_code}", "danger")

    return render_template("get_time_profiles.html", controller_id=controller_id)


##### cards #####

def get_door_states(controller_id):
    # Query door states
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/status"
    status_response = requests.get(url)

    if status_response.status_code == 200:
        status_data = status_response.json()
        door_states = status_data['status']['door-states']
    else:
        door_states = {}
    return door_states

def get_time_profiles(controller_id):
    # Make a GET request to retrieve the list of time profiles for the device
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time-profiles"
    response_timeprofile = requests.get(url)

    if response_timeprofile.status_code == 200:
        time_profiles_data = response_timeprofile.json()
    return time_profiles_data

@doorctl.route('/accesscontrol/controller/<int:controller_id>/cards', methods=['GET'])
@doorctl.route('/accesscontrol/controller/<int:controller_id>/card', methods=['GET'])
def show_cards(controller_id):
    door_states = get_door_states(controller_id)

    # Fetch the list of cards from the API
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/cards"
    response = requests.get(url)
    if response.status_code == 200:
        card_data = response.json()['cards']
    else:
        card_data = []

    time_profile_data = get_time_profiles(controller_id)

    return render_template('cards.html', time_profiles_data=time_profile_data, door_states=door_states, card_data=card_data, controller_id=controller_id)


@doorctl.route('/accesscontrol/controller/<int:controller_id>/card/<int:card_number>/show', methods=['GET'])
def get_card(controller_id, card_number):
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/card/{card_number}"
    response = requests.get(url)
    return render_template('get_card.html', controller_id=controller_id, card_data=response.json()['card'])


@doorctl.route('/accesscontrol/controller/<int:controller_id>/add_card', methods=['POST'])
def add_card(controller_id):
    door_states = get_door_states(controller_id)

    # Extract card details from the form data
    card_number = request.form['card_number']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    #doors = request.form['doors']
    doors = request.form.getlist('doors')
    pin = request.form['pin']

    # Create a card object to send to the API
    card_data = {
        'card-number': int(card_number),
        'start-date': start_date,
        'end-date': end_date,
        # 'doors': {"1":True,"2":False,"3":False,"4":True},
        'pin': int(pin) if pin != '' else None
    }
    card_data['doors'] = {}

    for i, value in enumerate(doors, start=1):
        if value == '0':
            card_data['doors'][str(i)] = 1
        elif value == '1':
            card_data['doors'][str(i)] = 0
        else:
            card_data['doors'][str(i)] = int(value)

    # Send a PUT request to add the card
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/card/{card_number}"
    response = requests.put(url, json=card_data)
    if response.status_code == 200:
        flash(f'Card {card_number} added successfully', 'success')
    else:
        error_message = response.json().get('message', 'Error adding card')
        response = response.json()['message']
        flash(
            f'Card {card_number} failed to add, server response: {response}', 'danger')

    print(card_data)
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/cards"
    response = requests.get(url)
    if response.status_code == 200:
        card_data = response.json()['cards']
    else:
        card_data = []

    time_profile_data = get_time_profiles(controller_id)
    return render_template('cards.html', time_profiles_data=time_profile_data, door_states=door_states, controller_id=controller_id, card_data=card_data)


@doorctl.route('/accesscontrol/controller/<int:controller_id>/delete_card', methods=['POST'])
def delete_card(controller_id):
    card_number = request.form['card_number']
    print(card_number)
    try:
        # Send a DELETE request to delete the card
        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/card/{card_number}"
        response = requests.delete(url)
        if response.status_code == 200:
            flash('Card deleted successfully', 'success')
        else:
            flash('Failed to delete card', 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('doorctl.show_cards', controller_id=controller_id))


@doorctl.route('/accesscontrol/controller/<int:controller_id>', methods=['GET'])
@doorctl.route('/accesscontrol/controller/<int:controller_id>/', methods=['GET'])
def controller_manage(controller_id):
    # Fetch the device time from the API
    event = None
    try:
        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/event/last"
        response = requests.get(url, headers={'accept': 'application/json'})
        event = response.json().get('event')
    except ValueError:
        # There's an issue with the response format (e.g., not a valid JSON)
        pass
    return render_template('controller_manage.html', event=event, controller_id=controller_id)


##### time routes #####
@doorctl.route('/accesscontrol/controller/<int:controller_id>/get_time', methods=['GET'])
def get_device_time(controller_id):
    # Fetch the device time from the API
    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        device_time = response.json()
        return f"Device current time: {device_time['datetime']}"
    elif response.status_code == 500:
        error = response.json()['message']
        error_message = f'Error getting time: {error}'
        return error_message

@doorctl.route('/accesscontrol/ajax/get_server_time')
# def get_server_time():
#     server_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     return json.dumps({"server_time": server_time})
def get_server_local_time():
    # Get the current local time that's timezone-aware
    local_time = datetime.datetime.now(tz=tz.tzlocal())

    # Return the formatted local time
    return json.dumps({"server_time": local_time.strftime("%Y-%m-%d %H:%M:%S")})

@doorctl.route('/accesscontrol/controller/<int:controller_id>/set_time', methods=['POST', 'GET'])
def set_device_time(controller_id):
    # Get the current date and time as a string
    server_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        current_device_time = response.json()['datetime']

    if request.method == 'POST':
        set_to_server_time = request.form.get('setToServerTime')  # Check if checkbox is checked

        if set_to_server_time:
            device_datetime = datetime.datetime.strptime(
                server_datetime, '%Y-%m-%d %H:%M:%S')  # Convert server_datetime to a datetime object
        else:
            # Get the datetime input from the form
            datetime_str = request.form.get('datetime')

            # Convert the input string to a datetime object
            try:
                device_datetime = datetime.datetime.strptime(
                    datetime_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                flash("Invalid datetime format. Please use 'YYYY-MM-DD HH:MM:SS'", 'danger')
                return render_template('set_device_time.html', controller_id=controller_id)

        # Prepare the request data
        request_data = {
            "datetime": device_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Set the device time using the API

        url = f"{current_app.config['REST_ENDPOINT']}/device/{controller_id}/time"
        response = requests.put(url, json=request_data, headers=HEADERS)

        if response.status_code == 200:
            device_time = response.json()
            flash(
                f"Device current time set to: {device_time['datetime']}", 'success')
        elif response.status_code == 500:
            error_message = response.json().get(
                'message', 'Error setting device date/time')
            flash(error_message, 'danger')
        else:
            flash("Failed to set device time", 'danger')

    return render_template('set_device_time.html', webserver_time=server_datetime, controller_id=controller_id, current_device_time=current_device_time)
