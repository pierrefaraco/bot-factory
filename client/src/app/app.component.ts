// src/app/app.component.ts
import { Component, OnInit, HostListener } from '@angular/core';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from './services/auth.service';
import { UsersService } from './services/users.service';
import { User } from './models/user.model';
import { USER_ROLES } from './constants/user-roles.constants';
import { ThemeService } from './services/theme.service';
import { MatIconModule } from '@angular/material/icon';
import { CustomDropDownMenuComponent } from './components/base/custom-dropdown-menu/custom-dropdown-menu.component';
import { MatDialog } from '@angular/material/dialog';
import { UserDialogComponent } from './components/admin/user-dialog/user-dialog.component';
import { PasswordDialogComponent } from './components/admin/password-dialog/password-dialog.component';
import { ButtonComponent } from './components/base/button/button.component';
import { filter } from 'rxjs/operators';
@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  standalone: true,
  imports: [RouterModule, CommonModule, MatIconModule, CustomDropDownMenuComponent,ButtonComponent]
})
export class AppComponent implements OnInit {
  parameterItemList = [
    {
      label: "Edit account",
      color: "var(--text-accent)",
      icon: "account_circle",
      action: () => {this.openProfilDialog()}
    },
    {
      label: "Change Password",
      color: "var(--text-accent)",
      icon: "account_circle",
      action: () => {this.openPasswordDialog()}
    },
    {
      label: "Help",
      link: "/help",
      color: "var(--text-accent)",
      icon: "help icon"
    }, {
      down: true,
      divider: true,
      color: "var(--text-primary)",
    }, {
      down: true,
      label: "Disconnect",
      link: "/landing",
      color: "var(--text-warning)",
      icon: "exit_to_app",
      action: () => { this.logout() }
    }


  ]

  isLoggedIn = false;
  isDarkMode: boolean = false;
  isDropdownOpen = false;
  showNavbar = true; // Contrôle l'affichage de la navbar

  myCurrentUser: User | null = null;

  constructor(
    private authService: AuthService,
    private usersService: UsersService,
    private themeService: ThemeService,
    private dialogRef: MatDialog,
    private router: Router
  ) {
    // S'abonner aux changements d'Ã©tat d'authentification
    this.isDarkMode = this.themeService.isDarkMode;
    this.authService['isAuthenticated$'].subscribe(
      (isAuthenticated: boolean) => {
        this.isLoggedIn = isAuthenticated;
        if (isAuthenticated) {
          this.loadUserProfile();
        }
      }
    );
  }



  ngOnInit() {
    this.isLoggedIn = this.authService.isAuthenticated();
    if (this.isLoggedIn) {
      this.loadUserProfile();
    }

    // Vérifier la route initiale
    this.checkRoute(this.router.url);

    // Écouter les changements de route
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.checkRoute(event.urlAfterRedirects || event.url);
      });
  }

  // Méthode pour vérifier si la navbar doit être affichée
  private checkRoute(url: string) {
    // Masquer la navbar sur les pages landing et login
    const hideNavbarRoutes = ['/landing', '/auth'];
    this.showNavbar = !hideNavbarRoutes.some(route => url.startsWith(route));
  }

  openProfilDialog(){

  
    const dialogRef = this.dialogRef.open(UserDialogComponent, {
      data: { isEditing: true, user:   this.myCurrentUser  },
       
    });

    dialogRef.afterClosed().subscribe(user=> {
      // Cancel closes the dialog with no value (see CustomDialogComponent.
      // onCancel / UserDialogComponent.onCancel) -- without this guard,
      // Cancel still fired PUT /users/me with an empty body, 400ing.
      if (!user) {
        return;
      }
      this.usersService.updateProfile(user).subscribe(
          (user)=>this.myCurrentUser = user
      )
    })
  }

  openPasswordDialog(){

    const dialogRef = this.dialogRef.open(PasswordDialogComponent)


    dialogRef.afterClosed().subscribe(passwords=> {
      // Same Cancel-closes-with-no-value case as openProfilDialog above.
      if (!passwords) {
        return;
      }
      // PUT /users/password/me returns {"msg": "..."}, not a user (see
      // change_password in rest_users_admin.py) -- assigning that response
      // to myCurrentUser used to clobber it, losing .email and blanking the
      // nav's mail-based user menu.
      this.usersService.updateProfilePassword({ old_password: passwords.old_password,new_password:  passwords.new_password}).subscribe()
    })
  }


  loadUserProfile() {
    this.usersService.getCurrentUser().subscribe({
      next: (user) => {
        this.myCurrentUser = user;
         console.log(this.myCurrentUser)
      },
      error: (error) => {
        console.error('Erreur lors du chargement du profil:', error);
      }
    });
  }
  get mail(): string | null {
    return this.myCurrentUser?.email ?? null;
  }

  get isAdmin() {
    return this.authService.currentjwtValue?.roles === USER_ROLES.ADMIN;
  }

  get isUser() {
    return this.authService.currentjwtValue?.roles === USER_ROLES.USER;
  }

  logout() {
    console.log('!!!!!!!logout')
    this.authService.logout();
  }

  toggleTheme() {
    this.themeService.toggleTheme();
    this.isDarkMode = this.themeService.isDarkMode;
  }

  toggleDropdown() {
    this.isDropdownOpen = !this.isDropdownOpen;
  }

  closeDropdown() {
    this.isDropdownOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: any) {
    const target = event.target;
    const dropdown = document.querySelector('.user-menu');
    const trigger = document.querySelector('#navbarDropdown');
    
    if (!dropdown?.contains(target) && !trigger?.contains(target)) {
      this.isDropdownOpen = false;
    }
  }
}