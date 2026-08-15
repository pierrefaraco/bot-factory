import { Routes } from '@angular/router';

export const alfred_routes: Routes = [
    {
        path: 'landing',
        loadComponent: () => import('./components/landing/landing.component').then(m => m.LandingComponent)
    },
    {
        path: 'login',
        redirectTo: 'auth',
        pathMatch: 'full'
    },
     {
        path: 'auth',
        loadComponent: () => import('./components/auth-form/auth-form.component').then(m => m.AuthFormComponent)
    },
    {
        path: 'workspace',
        loadComponent: () => import('./components/bot-workspace/bot-workspace.component').then(m => m.BotWorkspaceComponent)
    },
    // Routes héritées (redirection vers le nouveau workspace)
    {
        path: 'bot',
        redirectTo: 'workspace?tab=chat',
        pathMatch: 'full'
    },
    {
        path: 'token',
        redirectTo: 'workspace?tab=chat',
        pathMatch: 'full'
    },
    {
        path: 'data',
        redirectTo: 'workspace?tab=knowledge',
        pathMatch: 'full'
    },
     { 
        path: 'token-stats', 
        loadComponent: () => import('./components/token-stats/token-stats.component').then(m => m.TokenStatsComponent)
    },
    { 
        path: 'admin', 
        loadComponent: () => import('./components/admin/admin.component').then(m => m.AdminComponent)
    },
    {
        path: 'home',
        redirectTo: 'landing',
        pathMatch: 'full'
    },
    { 
        path: 'help', 
        loadComponent: () => import('./components/help/help.component').then(m => m.HelpComponent)
    },
    {
        path: 'policies',
        loadComponent: () => import('./components/policies/policies.component').then(m => m.PoliciesComponent)
    },
    { path: '', redirectTo: '/landing', pathMatch: 'full' },
];