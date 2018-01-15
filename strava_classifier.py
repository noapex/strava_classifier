# coding: utf-8
import os
import traceback
import datetime
import dateutil.parser
from stravalib.client import Client
from os.path import expanduser

# levantar actividades de las ultimas n horas
last_n_hours = 2400

# aplicar cambios. False para pruebas
write = False


locations = {
    'hudson': {
        'name': 'Río de hudson',
        'latlng': [-34.753652, -58.108775],
    },
    'mtb': {
        'name': 'Entrenamiento MTB',
        'latlng': [-34.694710, -58.259766],
    },
    'ceamse': {
        'name': 'CEAMSE',
        'latlng': [-34.685958, -58.278649]
    },
    'unq': {
        'name_go': 'Ida a la UNQ',
        'name_back': 'Vuelta de la UNQ',
        'latlng': [-34.707308, -58.278631],
        'commute': True,
        'private': True
    },
    'pato': {
        'name_go': 'Quilmes - El Pato',
        'name_back': 'El Pato - Quilmes',
        'latlng': [-34.890243,-58.150957],
        'commute': False,
        'private': False,
        'tolerance': 0.5,
    }

}


users = [
    {
        'user1': {
            'default_private': True,
            'token': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'bici_rodillo': 'b3666947',
            # con solo pasar aplica
            'pass_through_locations': [locations['hudson'], locations['ceamse'], locations['mtb']],
            # act. que matchean si se llega o se parte de las mismas
            'destinations': [locations['feli'], locations['unq'], locations['pato']]
        }
    },
    {
        'user2': {
            'default_private': False,
            'token': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'bici_rodillo': 'b4139947',
            # con solo pasar aplica
            'pass_through_locations': [locations['hudson'], locations['ceamse'], locations['mtb']],
            # act. que matchean si se llega o se parte de las mismas
            'destinations': [locations['feli'], locations['unq'], locations['pato']]
        }
    }
]


class StopLooking(Exception):
    pass


def in_zone(latlng1, latlng2, precision=0.2):
    from math import sin, cos, sqrt, atan2, radians

    # radio aprox. en lat -34.7
    R = 6370

    lat1 = radians(latlng1[0])
    lon1 = radians(latlng1[1])
    lat2 = radians(latlng2[0])
    lon2 = radians(latlng2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance < precision


def pass_through_zone(latlng1, latlng_stream, precision=0.2):
    for lat_lng in latlng_stream:
        if in_zone(lat_lng, latlng1, precision):
            return True
    return False


def write_last_activities(d):
    import json
    with open(data_file, "w") as f:
        f.write(json.dumps(d))


def get_last_processed(user):
    import json
    if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
        with open(data_file, "r") as f:
            j = json.loads(f.read())
            if user in j.keys():
                return j[user]
            else:
                return False
    else:
        return False


data_file = '{}/.strava.data'.format(expanduser('~'))
utcnow = datetime.datetime.utcnow()
after_date = (utcnow - datetime.timedelta(hours=last_n_hours)).isoformat()

activities = dict()
for user in users:
    for u, k in user.items():
        # if u == 'ramiro':
        #     continue
        client = Client()
        client.access_token = k['token']

        prev_activity = None

        try:
            print('-- {} --'.format(utcnow.isoformat()))
            last_processed_activities = get_last_processed(u)

            for activity in client.get_activities(after=after_date):
                current_activity_processed = False
                if not u in activities.keys():
                    activities[u] = list()
                activities[u].append(activity.id)
                if last_processed_activities and activity.id in last_processed_activities:
                    continue

                # Entrenamiento Funcional
                if activity.type == 'Workout':
                    print('ENTRENAMIENTO: ', end="")
                    print(
                        u"{0.suffer_score} {0.name} {0.moving_time} {0.distance} https://www.strava.com/activities/{0.id}".
                        format(activity))
                    if write:
                        client.update_activity(
                            activity.id,
                            private=True,
                            name='Entrenamiento funcional')
                    continue
                # Salida en bici
                elif activity.type == 'Ride':

                    # Actividad duplicada si el comienzo de la actual es menor al fin de la ultima
                    if prev_activity:
                        prev_activity_end_date = prev_activity.start_date + prev_activity.elapsed_time
                        if activity.start_date < prev_activity_end_date:
                            print('IGUALES: ')
                            print(
                                u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                format(prev_activity))
                            print(
                                u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                format(activity))

                            # Si es el Wahoo (registra temp), seteo la act previa en privada y la act en pub
                            if activity.average_temp:
                                if write:
                                    if k['default_private']:
                                        client.update_activity(
                                            activity.id, private=False)
                                    else:
                                        client.update_activity(
                                            prev_activity.id, private=True)


                            # Entonces la act. anterior es del Wahoo, la actual va en privada
                            else:
                                if write:
                                    if k['default_private']:
                                        client.update_activity(
                                            prev_activity.id, private=False)
                                    else:
                                        client.update_activity(
                                            activity.id, private=True)


                    # Actividad sin metros o de rodillo es rodillo
                    if activity.trainer or int(activity.distance) == 0:
                        print('RODILLO: ', end="")
                        print(
                            u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                            format(activity))
                        if write:
                            client.update_activity(
                                activity.id,
                                private=True,
                                gear_id=k['bici_rodillo'],
                                name='Rodillo')
                        prev_activity = activity
                        continue

                    # Destino configurado
                    for d in k['destinations']:
                        # Actividad ida
                        if 'tolerance' in d:
                            distance = d['tolerance']
                        else:
                            distance = 0.2

                        if activity.end_latlng and in_zone(activity.end_latlng, d['latlng'], distance):
                            print(d['name_go'], end="")
                            print(
                                u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                format(activity))
                            if write and any(
                                    x in activity.name
                                    for x in ('Pedalada', 'Ciclismo', 'Vuelta ciclista',
                                              'almuerzo')):
                                client.update_activity(
                                    activity.id,
                                    private=d['private'],
                                    commute=d['commute'],
                                    name=d['name_go'])
                            prev_activity = activity
                            current_activity_processed = True

                        # Actividad vuelta
                        if activity.end_latlng and in_zone(activity.end_latlng, d['latlng'], distance):
                            print(d['name_back'], end="")
                            print(
                                u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                format(activity))
                            if write and any(
                                    x in activity.name
                                    for x in ('Pedalada', 'Ciclismo', 'Vuelta ciclista',
                                              'Ride', 'almuerzo')):
                                client.update_activity(
                                    activity.id,
                                    private=d['private'],
                                    commute=d['commute'],
                                    name=d['name_back'])
                            prev_activity = activity
                            current_activity_processed = True

                    # Paso por lugar configurado
                    for p in k['pass_through_locations']:
                        # Solo act de mas de 20k
                        if activity.distance and int(
                                activity.distance) > 20000:
                            streams = client.get_activity_streams(
                                activity.id, ['latlng'], 'medium')
                            if 'latlng' in streams.keys():
                                if pass_through_zone(
                                        p['latlng'],
                                        streams['latlng'].data,
                                        precision=0.3):
                                    print(p['name'], end="")
                                    print(
                                        u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                        format(activity))
                                    if write and any(
                                            x in activity.name
                                            for x in ('Pedalada', 'Ciclismo', 'Vuelta ciclista',
                                                      'Ride', 'almuerzo')):
                                        client.update_activity(
                                            activity.id, name=p['name'])
                                    current_activity_processed = True
                                    prev_activity = activity


                    if not current_activity_processed:
                        # Suffer score pete
                        if activity.suffer_score and activity.suffer_score < 20 or int(
                                activity.distance) < 10000:
                            print('PETE < 20 suffer: ', end="")
                            print(
                                u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                format(activity))
                            if write:
                                if not k['default_private']:
                                    client.update_activity(
                                        activity.id, private=True)
                        # El resto de las actividades
                        else:
                            if k['default_private']:
                                print('se hace publica')
                                print(
                                    u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".
                                    format(activity))
                                if write:
                                    client.update_activity(
                                        activity.id, private=False)
                        #     print('No se toca: ', end="")
                        #     print(u": [{0.suffer_score}] \"{0.name}\" {0.moving_time} {0.distance} {0.start_date_local} https://www.strava.com/activities/{0.id}".format(activity))

                prev_activity = activity
        except Exception as e:
            print('ERROR', e)
            print(traceback.format_exc())

if write:
    write_last_activities(activities)
