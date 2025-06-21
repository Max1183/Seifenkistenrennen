export interface TeamFormData {
  name: string;
}

export interface SoapboxFormData {
  name: string;
}

export interface RacerFormData {
  first_name: string;
  last_name: string;
  soapbox_class: SoapboxClassValue;
  team: number | '' | null;
  soapbox: number | '' | null;
  start_number?: string | null;
}

export interface RaceRunFormData {
  racer_id?: number | null;
  racer_start_number?: string | null;
  time_in_seconds: string | null;
  disqualified: boolean;
  notes?: string | null;
  run_identifier: number;
  run_type: RaceRunTypeValue;
}

export interface TeamFromAPI {
  id: number;
  name: string;
  racer_count?: number;
  racers_info?: { id: number; first_name: string; last_name: string }[];
  created_at?: string;
  updated_at?: string;
}

export interface SoapboxFromAPI {
  id: number;
  name: string;
  created_at?: string;
  updated_at?: string;
}

export interface RaceRunFromAPI {
  id: number;
  racer: number;
  racer_name?: string;
  run_type: RaceRunTypeValue;
  run_type_display: string;
  run_identifier: number;
  time_in_seconds: string | null;
  disqualified: boolean;
  notes?: string | null;
  recorded_at?: string;
}

export interface RacerFromAPI {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  soapbox_class: SoapboxClassValue;
  soapbox_class_display: string;
  team: number | null;
  team_name: string | null;
  soapbox: number | null;
  soapbox_name: string | null;
  start_number: string | null;
  best_time_seconds: string | null;
  races: RaceRunFromAPI[];
  created_at?: string;
  updated_at?: string;
  rank?: number;
}

export type SoapboxClassValue = 'LRJ' | 'LRS' | 'HRJ' | 'HRS' | 'XKL' | 'VTR' | 'UNK';

export const SOAPBOX_CLASS_VALUES = {
  LUFTREIFEN_JUNIOR: 'LRJ' as SoapboxClassValue,
  LUFTREIFEN_SENIOR: 'LRS' as SoapboxClassValue,
  HARTREIFEN_JUNIOR: 'HRJ' as SoapboxClassValue,
  HARTREIFEN_SENIOR: 'HRS' as SoapboxClassValue,
  X_KLASSE: 'XKL' as SoapboxClassValue,
  VETERANEN: 'VTR' as SoapboxClassValue,
  UNKNOWN: 'UNK' as SoapboxClassValue,
} as const;

export const SOAPBOX_CLASS_DISPLAY_MAP: Record<SoapboxClassValue, string> = {
  LRJ: 'Luftreifen Junior',
  LRS: 'Luftreifen Senior',
  HRJ: 'Hartreifen Junior',
  HRS: 'Hartreifen Senior',
  XKL: 'X-Klasse',
  VTR: 'Veteranen',
  UNK: 'Unbekannt',
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

export const DISPLAYED_RUN_TYPES_ORDER: RaceRunTypeValue[] = [
    RACE_RUN_TYPE_VALUES.PRACTICE,
    RACE_RUN_TYPE_VALUES.HEAT_1,
    RACE_RUN_TYPE_VALUES.HEAT_2,
];