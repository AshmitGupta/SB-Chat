from neo4j import GraphDatabase
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Replace these with your Neo4j connection details
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

XML_FILES = ['service_bulletin_1.xml', 'service_bulletin_2.xml']

def parse_service_bulletin(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    sb_data = {
        'docnumber': '',
        'required_man_hours': 0,
        'description': '',
        'urgency_level': '',
        'applicability': [],
        'is_mandatory': False,
        'compliance_deadline': None,
        'parts': []
    }

    sb_data['docnumber'] = root.findtext('Header/Title', default='').split()[-1]
    sb_data['description'] = root.findtext('Header/Subject', default='')
    compliance = root.find('Compliance')
    if compliance is not None:
        sb_data['is_mandatory'] = compliance.findtext('AirworthinessDirective', default='No') == 'Yes'
    effectivity = root.find('Effectivity/Airplanes/LineNumbers')
    if effectivity is not None:
        line_numbers = effectivity.text.replace(' ', '').split(',')
        sb_data['applicability'] = [f"Aircraft_{ln}" for ln in line_numbers]

    sb_data['urgency_level'] = 'High' if sb_data['is_mandatory'] else 'Low'
    if sb_data['is_mandatory']:
        sb_data['compliance_deadline'] = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')


    parts_section = root.find('MaterialInformation/PartsNecessary/KitsParts')
    if parts_section is not None:
        for part_elem in parts_section.findall('Part'):
            part = {
                'part_number': part_elem.findtext('PartNumber', default=''),
                'name': part_elem.findtext('Description', default=''),
                'price': 1000,
                'availability': True,
                'lead_time': 0 
            }
            sb_data['parts'].append(part)

    return sb_data

def create_graph():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        for i in range(1, 21):
            query = """
            CREATE (:Aircraft {
                name: $name,
                mean_time_between_failures: $mtbf,
                unexpected_removal_time: $urt,
                service_interruptions: $si,
                downtime_from_maintenance: $dtfm,
                time_on_wing: $tow,
                age: $age,
                operational_cost_per_hour: $ocph,
                current_status: $current_status,
                next_scheduled_maintenance: $next_scheduled_maintenance
            })
            """
            next_maintenance = datetime.now() + timedelta(days=i * 15)
            parameters = {
                'name': f"Aircraft_{i}",
                'mtbf': 4000 + i * 100,
                'urt': 50 - i,
                'si': i % 5 + 1,
                'dtfm': 150 + i * 10,
                'tow': 3000 + i * 200,
                'age': i % 10 + 1,
                'ocph': 900 + i * 10,
                'current_status': "In Service" if i % 3 else "Scheduled for Maintenance",
                'next_scheduled_maintenance': next_maintenance.strftime('%Y-%m-%d')
            }
            session.run(query, parameters)

        for xml_file in XML_FILES:
            sb_data = parse_service_bulletin(xml_file)

            sb_query = """
            CREATE (sb:ServiceBulletin {
                docnumber: $docnumber,
                required_man_hours: $required_man_hours,
                description: $description,
                urgency_level: $urgency_level,
                applicability: $applicability,
                is_mandatory: $is_mandatory,
                compliance_deadline: $compliance_deadline
            })
            """
            session.run(sb_query, sb_data)

            for part in sb_data['parts']:
                part_exists = session.run("MATCH (p:Part {part_number: $part_number}) RETURN p", part_number=part['part_number']).single()
                if not part_exists:
                    part_query = """
                    CREATE (:Part {
                        part_number: $part_number,
                        name: $name,
                        price: $price,
                        availability: $availability,
                        lead_time: $lead_time
                    })
                    """
                    session.run(part_query, part)

                rel_query = """
                MATCH (sb:ServiceBulletin {docnumber: $docnumber}), (p:Part {part_number: $part_number})
                CREATE (sb)-[:REQUIRES_PART {quantity_required: $quantity_required}]->(p)
                """
                parameters = {
                    'docnumber': sb_data['docnumber'],
                    'part_number': part['part_number'],
                    'quantity_required': 1
                }
                session.run(rel_query, parameters)

            for aircraft_name in sb_data['applicability']:
                aircraft_exists = session.run("MATCH (a:Aircraft {name: $name}) RETURN a", name=aircraft_name).single()
                if not aircraft_exists:
                    query = """
                    CREATE (:Aircraft {
                        name: $name,
                        mean_time_between_failures: $mtbf,
                        unexpected_removal_time: $urt,
                        service_interruptions: $si,
                        downtime_from_maintenance: $dtfm,
                        time_on_wing: $tow,
                        age: $age,
                        operational_cost_per_hour: $ocph,
                        current_status: $current_status,
                        next_scheduled_maintenance: $next_scheduled_maintenance
                    })
                    """
                    next_maintenance = datetime.now() + timedelta(days=180)
                    parameters = {
                        'name': aircraft_name,
                        'mtbf': 5000,
                        'urt': 45,
                        'si': 2,
                        'dtfm': 200,
                        'tow': 4000,
                        'age': 5,
                        'ocph': 950,
                        'current_status': "In Service",
                        'next_scheduled_maintenance': next_maintenance.strftime('%Y-%m-%d')
                    }
                    session.run(query, parameters)

                rel_query = """
                MATCH (sb:ServiceBulletin {docnumber: $docnumber}), (a:Aircraft {name: $aircraft_name})
                CREATE (sb)-[:APPLICABLE_TO]->(a)
                """
                parameters = {
                    'docnumber': sb_data['docnumber'],
                    'aircraft_name': aircraft_name
                }
                session.run(rel_query, parameters)

    driver.close()
    print("Graph creation complete.")

if __name__ == "__main__":
    create_graph()
