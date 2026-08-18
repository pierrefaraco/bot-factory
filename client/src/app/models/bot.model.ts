import { Avatar } from "./avatar.model";
import { BotParameters} from "./bot-parameters.model";

export interface Bot {
    id: number;
    user_account_id?: number;
    avatar?: Avatar
    bot_parameters?: BotParameters
  }