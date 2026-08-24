export interface Knowledge {
  id: number;
  name: string;
  content: string;
  indice: number;
  knowledge_dad_id: string;
  children_ref_id: string;
  children?: Knowledge[];
  level: number;
  pdf_file: string | null;
  updated_at?: string;
  vector_synced_at?: string | null;
}

export interface FlatChapterNode {
  id: number;
  name: string;
  content: string;
  indice: number;
  level: number;
  expandable: boolean;
  updated_at?: string;
  vector_synced_at?: string | null;
}