import { AssignedBot } from "./assigned_bot.model";

export interface User {
    id: number;
    email: string;
    password: string;
    name: string;
    roles: string;
    parent_id: number;
    is_active: boolean;
    selected_bot_id: number;
    assigned_bot_ids?: number[];
    assigned_bots?: AssignedBot[];
    parent_email?: string;
    owned_bots_count?: number;
    created_at?: string;
}