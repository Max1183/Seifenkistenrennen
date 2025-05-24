export interface TeamData { // Für Formulare
  name: string;
  // description?: string;
}

export interface RacerData { // Für Formulare
  first_name: string;
  last_name: string;
  date_of_birth: string; // Im Format YYYY-MM-DD für das <input type="date">
  team: number | null; // ID des Teams
}

export interface TeamFromAPI {
  id: number;
  name: string;
  racer_count?: number;
  racers?: RacerFromAPI[]; // Ggf. detailliertere Typen für Racer
}

export interface RacerFromAPI {
  id: number;
  first_name: string;
  last_name: string;
  full_name?: string;
  date_of_birth: string;
  team: number | null;
  team_details?: { id: number, name: string }; // Wenn das Backend Teamdetails mitsendet
}

export interface RaceRunFrontend {
  id: number;
  run_type: string; // 'PR', 'H1', 'H2'
  run_type_display: string; // 'Practice', 'Heat 1', 'Heat 2'
  run_identifier: number;
  time_in_seconds: string | null; // Kommt als String vom DecimalField
  disqualified: boolean;
  notes?: string | null;
}

export interface RacerFrontend {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  soapbox_class: string; // 'LJ', 'LS', etc.
  soapbox_class_display: string;
  team: number | null;
  team_name: string | null;
  start_number: string | null;
  best_time_seconds: string | null; // Kommt als String vom DecimalField
  races: RaceRunFrontend[];
  // Optional, wenn vom Backend berechnet oder im Frontend hinzugefügt
  rank?: number;
}

export interface TeamFrontend { // Falls du auch Team-Infos separat laden/anzeigen willst
  id: number;
  name: string;
  racer_count?: number;
  racers_info?: { id: number; first_name: string; last_name: string }[];
}

export interface SoapboxClassOption {
  value: string;
  label: string;
}