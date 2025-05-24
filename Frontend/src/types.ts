export interface TeamFormData {
  name: string;
}

export interface RacerFormData {
  first_name: string;
  last_name: string;
  soapbox_class: SoapboxClassValue;
  date_of_birth: string; // Expects YYYY-MM-DD format for <input type="date">
  team: number | '' | null; // number for ID, '' for empty select, null for "no team" to API
  start_number?: string | null;
}

export interface RaceRunFormData {
  racer: number; // Racer ID
  time_in_seconds: string | null; // Input as string, then parse. Null if no time.
  disqualified: boolean;
  notes?: string | null;
  run_identifier: number;
  run_type: RaceRunTypeValue;
}

export interface TeamFromAPI {
  id: number;
  name: string;
  racer_count?: number; // Often calculated by the backend
  racers_info?: { id: number; first_name: string; last_name: string }[]; // Simplified racer info
  created_at?: string; // ISO date string
  updated_at?: string; // ISO date string
}

export interface RaceRunFromAPI {
  id: number;
  racer: number; // ID of the Racer
  racer_name?: string; // Often added by serializer (source='racer.full_name')
  run_type: RaceRunTypeValue; // 'PR', 'H1', 'H2'
  run_type_display: string; // 'Practice', 'Heat 1', 'Heat 2'
  run_identifier: number;
  time_in_seconds: string | null; // Backend DecimalField comes as string
  disqualified: boolean;
  notes?: string | null;
  recorded_at?: string; // ISO date string
}

export interface RacerFromAPI {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string; // From backend @property
  soapbox_class: SoapboxClassValue; // 'LJ', 'LS', etc.
  soapbox_class_display: string; // From backend get_..._display
  date_of_birth: string | null; // ISO date string or null
  age?: number | null; // Can be calculated by backend or frontend
  team: number | null; // ID of the team or null
  team_name: string | null; // Name of the team (source='team.name')
  start_number: string | null;
  best_time_seconds: string | null; // Backend DecimalField comes as string
  races: RaceRunFromAPI[]; // Array of race runs
  created_at?: string; // ISO date string
  updated_at?: string; // ISO date string
  rank?: number;
}

export type SoapboxClassValue = 'LJ' | 'LS' | 'HJ' | 'HS' | 'XK' | 'VT' | 'UN';

export const SOAPBOX_CLASS_VALUES = {
  LUFTREIFEN_JUNIOR: 'LJ' as SoapboxClassValue,
  LUFTREIFEN_SENIOR: 'LS' as SoapboxClassValue,
  HARTREIFEN_JUNIOR: 'HJ' as SoapboxClassValue,
  HARTREIFEN_SENIOR: 'HS' as SoapboxClassValue,
  X_KLASSE: 'XK' as SoapboxClassValue,
  VETERANEN: 'VT' as SoapboxClassValue,
  UNKNOWN: 'UN' as SoapboxClassValue,
} as const;

export const SOAPBOX_CLASS_DISPLAY_MAP: Record<SoapboxClassValue, string> = {
  LJ: 'Luftreifen Junior',
  LS: 'Luftreifen Senior',
  HJ: 'Hartreifen Junior',
  HS: 'Hartreifen Senior',
  XK: 'X-Klasse',
  VT: 'Veteranen',
  UN: 'Unbekannt',
};

export interface SoapboxClassOption {
  value: SoapboxClassValue;
  label: string;
}

export type RaceRunTypeValue = 'PR' | 'H1' | 'H2';

export const RACE_RUN_TYPE_VALUES = {
  PRACTICE: 'PR' as RaceRunTypeValue,
  HEAT_1: 'H1' as RaceRunTypeValue,
  HEAT_2: 'H2' as RaceRunTypeValue,
} as const;

export const RACE_RUN_TYPE_DISPLAY_MAP: Record<RaceRunTypeValue, string> = {
  PR: 'Probelauf',
  H1: '1. Wertungslauf',
  H2: '2. Wertungslauf',
};

// Defines the order of run types columns in tables and potentially other displays
export const DISPLAYED_RUN_TYPES_ORDER: RaceRunTypeValue[] = [
    RACE_RUN_TYPE_VALUES.PRACTICE,
    RACE_RUN_TYPE_VALUES.HEAT_1,
    RACE_RUN_TYPE_VALUES.HEAT_2,
];