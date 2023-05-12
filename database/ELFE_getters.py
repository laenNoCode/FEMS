from typing import List, Dict, Union
from dataclasses import dataclass
from database.query import fetch
from database.ELFE_db_types import ELFE_database_names
from psycopg2 import sql

MODE_PILOTE = 30

@dataclass
class MachineToScheduleType():
	Id             : int
	cycle_name     : str
	zabbix_id      : int
	end_timestamp  : int
	max_delay      : int
	equipment_type : int
def get_machines_to_schedule(credentials) -> List[MachineToScheduleType]:
	query = (sql.SQL(f" SELECT machine.equipement_pilote_ou_mesure_id, cycle.nom, machine.mesures_puissance_elec_id, machine.timestamp_de_fin_souhaite, machine.delai_attente_maximale_apres_fin, equipement.equipement_pilote_ou_mesure_type_id"
			+ " FROM {0} AS machine" 
	    	+ " INNER JOIN {1} AS cycle ON cycle.id = machine.cycle_equipement_pilote_machine_generique_id " 
			+ " INNER JOIN {2} AS equipement ON machine.equipement_pilote_ou_mesure_id = equipement.id "
			+ " WHERE equipement.equipement_pilote_ou_mesure_mode_id = %s;").format(
				sql.Identifier(ELFE_database_names['ELFE_MachineGenerique']),
    			sql.Identifier(ELFE_database_names['ELFE_MachineGeneriqueCycle']),
				sql.Identifier(ELFE_database_names['ELFE_EquipementPilote'])
			),  [MODE_PILOTE])
	result = fetch(credentials, query)
	result_typed : List[MachineToScheduleType] = [MachineToScheduleType(r[0], r[1], r[2], r[3], r[4], r[5]) for r in result]
	return result_typed
@dataclass
class ECSToScheduleType():
	Id             : int
	zabbix_id      : int
	volume_L       : str
	power_W        : int
	start          : int
	end            : int
	equipment_type : int

def get_ECS_to_schedule(credentials, timestamp, ECS_not_to_schedule: Union[List[int], None] = None) -> List[ECSToScheduleType]:
	query = (sql.SQL(" SELECT epm.id, ecs.mesures_puissance_elec_id ,ecs.volume_ballon, ecs.puissance_chauffe, hc.debut, hc.fin, epm.equipement_pilote_ou_mesure_type_id"
			+ " FROM {0} AS epm" 
	    	+ " INNER JOIN {1} AS ecs ON epm.id=ecs.equipement_pilote_ou_mesure_id" 
			+ " INNER JOIN {2} AS hc ON ecs.id = hc.equipement_pilote_ballon_ecs_id"
			+ " WHERE hc.actif=true and epm.equipement_pilote_ou_mesure_mode_id=%s AND epm.timestamp_derniere_mise_en_marche + 12 * 3600 <= %s").format(
				sql.Identifier(ELFE_database_names['ELFE_EquipementPilote']),
				sql.Identifier(ELFE_database_names['ELFE_BallonECS']),
				sql.Identifier(ELFE_database_names['ELFE_BallonECSHeuresCreuses'])
			), 
			[MODE_PILOTE, timestamp])
	result = fetch(credentials, query)
	result_typed : List[ECSToScheduleType] = [ECSToScheduleType(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in result]
	
	#gets only the biggest period where it can be scheduled
	biggest_period_ecs : Dict[int, ECSToScheduleType] = {}
	for ecs in result_typed:
		if ECS_not_to_schedule != None and ecs.Id in ECS_not_to_schedule:
			continue
		if ecs.Id not in biggest_period_ecs:
			biggest_period_ecs[ecs.Id] = ecs
		elif (ecs.end - ecs.start > biggest_period_ecs[ecs.Id].end - biggest_period_ecs[ecs.Id].start):
			biggest_period_ecs[ecs.Id] = ecs
	return biggest_period_ecs