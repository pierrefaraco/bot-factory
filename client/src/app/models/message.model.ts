export interface Message {
    id: number;
    content: string;
    order:number;
    time:Date;
    role: string;
    session_id: number;
}