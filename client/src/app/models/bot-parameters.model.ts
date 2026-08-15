
export interface BotParameters {
    id?: number;
    bot_id?: number;
    bot_name?: string;
    bot_type?: string;
    main_personality_trait_1?: string
    main_personality_trait_2?:string
    main_personality_trait_3?:string
    used_sources?: string;
    context_type?: string;
    answer_style?: string;
    answer_length?:string;
    interlocutor_type?:string;
    goal?: string;
    behaviour_when_ignore?:string;
    behaviour_with_language?:string;
    localisation?: string;
    interlocutor_identity?: string;
    answer_format?: string;
    voice_output?: boolean;
    persona_description?: string;
  }