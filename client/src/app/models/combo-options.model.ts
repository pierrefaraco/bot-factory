export interface CustomOption{
  description: string;
  label: string;

}


export interface ComboOptions {
  answer_format: CustomOption[];
  answer_length: CustomOption[];
  answer_style: CustomOption[];
  behaviour: CustomOption[];
  behaviour_when_finish_speak: CustomOption[];
  behaviour_when_ignore: CustomOption[];
  behaviour_with_language: CustomOption[];
  context_type: CustomOption[];
  flaws: {
    greed: string[];
    social_character: string[];
    cruelty: string[];
    egocentrism: string[];
    stubbornness: string[];
    excess: string[];
    instability: string[];
    cowardice: string[];
    dishonesty: string[];
    pride: string[];
    laziness: string[];
  };
  goal: CustomOption[];
  quality: {
    emotional: string[];
    intellectual: string[];
    moral: string[];
    professional: string[];
    social: string[];
    spiritual: string[];
  };
  used_sources: CustomOption[];
  interlocutor_identity:CustomOption[];
}


export function transformToCustomOptions(comboOptions: ComboOptions): CustomOption[] {
  const customOptions: CustomOption[] = [];

  // 'defauts' is the legacy key served by API instances started before the
  // qualities_flaws.yaml rename; accept both until every server is restarted.
  const quality = comboOptions.quality ?? {};
  const flaws = comboOptions.flaws ?? (comboOptions as any).defauts ?? {};

  for (const group of [quality, flaws]) {
    Object.values(group).forEach((items: string[]) => {
      items.forEach(item => {
        customOptions.push({
          description: item,
          label: item,
        });
      });
    });
  }

  return customOptions;
}
