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