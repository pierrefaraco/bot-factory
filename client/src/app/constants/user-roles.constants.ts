import { HttpHeaders } from "@angular/common/http";
import { environment } from "../../environments/environment";


export const USER_ROLES = {
    ADMIN : "Admin",
    USER : "User",
    GUEST : "Guest",
} as const;


export const API_URL = environment.apiUrl;
export const HTTP_OPTIONS = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      // 'Cache-Control': 'no-cache',
      // 'Pragma': 'no-cache',
      // 'Expires': '0'
    }),
    withCredentials: true // Important si vous utilisez des cookies
  };
