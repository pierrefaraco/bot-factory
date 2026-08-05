export interface CustomOption{
  description: string;
  label: string;

}


export interface ComboOptions {
  answer_length: CustomOption[];
  answer_style: CustomOption[];
  behaviour: CustomOption[];
  behaviour_when_finish_speak: CustomOption[];
  behaviour_when_ignore: CustomOption[];
  behaviour_with_language: CustomOption[];
  context_type: CustomOption[];
  defauts: {
    avarice: string[];
    caractere_social: string[];
    cruaute: string[];
    egocentrisme: string[];
    entetement: string[];
    exces: string[];
    instabilite: string[];
    lachete: string[];
    malhonnete: string[];
    orgueil: string[];
    paresse: string[];
  };
  goal: CustomOption[];
  quality: {
    emotionnels: string[];
    intellectuels: string[];
    moraux: string[];
    professionnels: string[];
    sociaux: string[];
    spirituels: string[];
  };
  used_sources: CustomOption[];
  interlocutor_identity:CustomOption[];
}


export function transformToCustomOptions(comboOptions: ComboOptions): CustomOption[] {
  const customOptions: CustomOption[] = [];

  // Transform 'quality'
  const qualityCategories = Object.keys(comboOptions.quality) as (keyof typeof comboOptions.quality)[];
  qualityCategories.forEach(category => {
    comboOptions.quality[category].forEach(item => {
      customOptions.push({
        description: item,
        label: item,
      });
    });
  });

  // Transform 'defauts'
  const defautsCategories = Object.keys(comboOptions.defauts) as (keyof typeof comboOptions.defauts)[];
  defautsCategories.forEach(category => {
    comboOptions.defauts[category].forEach(item => {
      customOptions.push({
        description: item,
        label: item,
      });
    });
  });

  return customOptions;
}
