import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { UsersService } from '../../services/users.service';
import { User } from '../../models/user.model';
import { BotService } from '../../services/bot.service';
import { Bot } from '../../models/bot.model';
import { UserDialogComponent } from './user-dialog/user-dialog.component';
import { PasswordDialogComponent } from './password-dialog/password-dialog.component';
import { BotAssignmentDialogComponent } from './bot-assignment-dialog/bot-assignment-dialog.component';
import { ConfirmDialogComponent } from '../base/confirm-dialog/confirm-dialog.component';
import { finalize } from 'rxjs/operators';
import { ArrayComponent } from '../base/array/array.component';
import { LineComponent } from '../base/array/line/line.component';
import { ColumnComponent } from '../base/array/column/column.component';
import { ButtonComponent } from '../base/button/button.component';
import { CustomDropDownMenuComponent } from '../base/custom-dropdown-menu/custom-dropdown-menu.component';
import { AuthService } from '../../services/auth.service';
import { SuccessNotificationService } from '../../services/success-notification.service';
import { TokenStatsService } from '../../services/token-stats.service';
import { AdminTokenUsageSummary } from '../../models/token-stats.model';
import { USER_ROLES } from '../../constants/user-roles.constants';

type StatusFilter = 'all' | 'active' | 'inactive';

@Component({
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatIconModule,
    MatDialogModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    UserDialogComponent,
    PasswordDialogComponent,
    BotAssignmentDialogComponent,
    ConfirmDialogComponent,
    ArrayComponent,
    LineComponent,
    ColumnComponent,
    ButtonComponent,
    CustomDropDownMenuComponent
  ],
  selector: 'app-user-registration',
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  guestUsers: User[] = [];
  allUsers: User[] = [];
  guestsLoading = false;
  usersLoading = false;
  activeTab: 'overview' | 'users' | 'settings' = 'overview';
  // ADMIN excluded: PUT /users/<id>/role's RoleChangeRequest (server-side)
  // no longer accepts it as a target role -- there is no API path to
  // create a second Admin account at all.
  roleOptions: string[] = [USER_ROLES.USER, USER_ROLES.GUEST];

  guestColumns = ['Email', 'Status', 'Assigned Bots', 'Tokens (24h)', 'Tokens (30d)', 'Created', 'Actions'];
  userColumns = ['Email', 'Role', 'Status', 'Parent', 'Bots', 'Tokens (24h)', 'Tokens (30d)', 'Created', 'Actions'];

  // Keyed by id (accounts by User.id, guests by their own id) -- loaded once
  // in ngOnInit via loadTokenUsageSummary(), not tied to guest/user reloads
  // since admin CRUD actions (create/delete/activate...) never change token
  // consumption.
  tokenUsageSummary: AdminTokenUsageSummary = { accounts: {}, guests: {} };

  guestStatusFilter: StatusFilter = 'all';
  userStatusFilter: StatusFilter = 'all';
  userRoleFilter: string = 'all';

  // Champs (pas des getters) recalculés explicitement à la demande : un
  // getter réévalué à chaque cycle de détection de changements renverrait
  // une nouvelle référence de tableau en continu, et ArrayComponent
  // réinitialise sa page courante dès que la référence de [records] change
  // (cf. ArrayComponent.ngOnChanges) -- la pagination ne pourrait jamais
  // avancer au-delà de la page 1.
  filteredGuestUsers: User[] = [];
  filteredAllUsers: User[] = [];

  guestSortableColumns: { [column: string]: (a: User, b: User) => number } = {
    'Email': (a, b) => (a.email || '').localeCompare(b.email || ''),
    'Assigned Bots': (a, b) => (a.assigned_bots?.length || 0) - (b.assigned_bots?.length || 0),
    'Status': (a, b) => Number(a.is_active) - Number(b.is_active),
    'Tokens (24h)': (a, b) => this.guestTokens24h(a) - this.guestTokens24h(b),
    'Tokens (30d)': (a, b) => this.guestTokens30d(a) - this.guestTokens30d(b),
    'Created': (a, b) => this.createdAtMs(a) - this.createdAtMs(b),
  };

  userSortableColumns: { [column: string]: (a: User, b: User) => number } = {
    'Email': (a, b) => (a.email || '').localeCompare(b.email || ''),
    'Role': (a, b) => (a.roles || '').localeCompare(b.roles || ''),
    'Parent': (a, b) => (a.parent_email || '').localeCompare(b.parent_email || ''),
    'Bots': (a, b) => this.botsCountFor(a) - this.botsCountFor(b),
    'Status': (a, b) => Number(a.is_active) - Number(b.is_active),
    'Tokens (24h)': (a, b) => this.userTokens24h(a) - this.userTokens24h(b),
    'Tokens (30d)': (a, b) => this.userTokens30d(a) - this.userTokens30d(b),
    'Created': (a, b) => this.createdAtMs(a) - this.createdAtMs(b),
  };

  // Activate/Deactivate's label, icon and action all depend on the row's
  // current is_active, so it can't be a static item like the rest of the
  // list -- built fresh per row by getGuestActionItems/getUserActionItems
  // below instead.
  private toggleStatusItem(user: User) {
    return {
      label: user.is_active ? "Deactivate" : "Activate",
      color: "var(--text-accent)",
      icon: user.is_active ? "pause" : "play_arrow",
      action: (user) => {this.toggleUserStatus(user)}
    };
  }

  getGuestActionItems(user: User) {
    return [
      this.toggleStatusItem(user),
      {
        label: "Edit User",
        color:  "var(--text-accent)",
        icon: "edit",
        action: (user) => {this.editUser(user)}
      },
      {
        label: "Assign Bot",
        color: "var(--text-accent)",
        icon: "smart_toy",
        action: (user) => {this.assignBot(user)}
      },
      {
        label: "Change Password",
        color: "var(--text-accent)",
        icon: "lock",
        action: (user) => {this.openPasswordModal(user)}
      },
      {
        divider: true,
        color:"var(--text-primary)"
      }, {
        label: "Delete",
        color: "var(--text-danger)",
        icon: "delete",
        action:  (user) => {this.deleteUser(user)}
      }
    ];
  }

  // "Edit User"/"Change Password" left out on purpose: PUT /users/password/
  // guest/<id> only ever authorizes the caller's own children
  // (guest.parent_id == caller_id, no admin bypass -- unlike every other
  // merged /users/<id> route), so it would 403 for most rows in this
  // platform-wide list. Role change has its own dedicated inline control
  // instead of living in this menu.
  getUserActionItems(user: User) {
    return [
      this.toggleStatusItem(user),
      {
        label: "Assign Bot",
        color: "var(--text-accent)",
        icon: "smart_toy",
        action: (user) => {this.assignBot(user)}
      },
      {
        divider: true,
        color: "var(--text-primary)"
      }, {
        label: "Delete",
        color: "var(--text-danger)",
        icon: "delete",
        action: (user) => {this.deleteUser(user)}
      }
    ];
  }

  constructor(
    private dialog: MatDialog,
    private usersService: UsersService,
    private botService: BotService,
    private authService: AuthService,
    private successNotificationService: SuccessNotificationService,
    private tokenStatsService: TokenStatsService
  ) {}

  ngOnInit(): void {
    this.loadGuestUsers();
    // GET /users is role_required([ADMIN_ROLE]) -- a User caller would
    // always get a guaranteed 403 here (and never see the Users tab that
    // consumes it, since it's hidden below), so there's no reason to fire
    // the request at all.
    if (this.isAdmin) {
      this.loadAllUsers();
    }
    this.loadTokenUsageSummary();
  }

  loadTokenUsageSummary(): void {
    this.tokenStatsService.getAdminTokenUsageSummary().subscribe({
      next: summary => this.tokenUsageSummary = summary,
      error: error => console.error('Error loading token usage summary:', error),
    });
  }

  guestTokens24h(user: User): number {
    return this.tokenUsageSummary.guests[user.id]?.tokens_24h || 0;
  }

  guestTokens30d(user: User): number {
    return this.tokenUsageSummary.guests[user.id]?.tokens_30d || 0;
  }

  userTokens24h(user: User): number {
    return this.tokenUsageSummary.accounts[user.id]?.tokens_24h || 0;
  }

  userTokens30d(user: User): number {
    return this.tokenUsageSummary.accounts[user.id]?.tokens_30d || 0;
  }

  get currentUserId(): number | null {
    return this.authService.get_curent_user_id();
  }

  get isAdmin(): boolean {
    return this.authService.getUserRole() === USER_ROLES.ADMIN;
  }

  applyGuestFilters(): void {
    this.filteredGuestUsers = this.guestUsers.filter(user => this.matchesStatus(user, this.guestStatusFilter));
  }

  applyUserFilters(): void {
    this.filteredAllUsers = this.allUsers.filter(user =>
      this.matchesStatus(user, this.userStatusFilter) &&
      (this.userRoleFilter === 'all' || user.roles === this.userRoleFilter)
    );
  }

  private matchesStatus(user: User, filter: StatusFilter): boolean {
    if (filter === 'active') return user.is_active;
    if (filter === 'inactive') return !user.is_active;
    return true;
  }

  private botsCountFor(user: User): number {
    return user.roles === 'Guest' ? (user.assigned_bots?.length || 0) : (user.owned_bots_count || 0);
  }

  private createdAtMs(user: User): number {
    return user.created_at ? new Date(user.created_at).getTime() : 0;
  }

  setActiveTab(tab: 'overview' | 'users' | 'settings'): void {
    this.activeTab = tab;
  }

  createEmptyUser(): User {
    return {
      id: -1,
      email: '',
      password: '',
      name: '',
      roles: '',
      parent_id: -1,
      is_active: false,
      selected_bot_id: -1,
      assigned_bot_ids: []
    };
  }

  on_open_create_modal() {
    const dialogRef = this.dialog.open(UserDialogComponent, {
      data: { isEditing: false, user:  this.createEmptyUser() },

    });

    dialogRef.afterClosed().subscribe(user=> {
      if (user) {
        this.usersService.registerGuest(user)
          .subscribe({
            next: () => {
              this.loadGuestUsers();
            },
            error: (error) => {
              console.error('Error creating user:', error);
            }
          });
      }
    });
  }

  editUser(user: User) {
    const dialogRef = this.dialog.open(UserDialogComponent, {
      data: { isEditing: true, user }
    });

    dialogRef.afterClosed().subscribe(_user => {
      if (_user) {
        this.usersService.updateGuest(user.id, _user)
          .subscribe({
            next: () => {
              this.loadGuestUsers();
            },
            error: (error) => {
              console.error('Error updating user:', error);
            }
          });
      }
    });
  }

  openPasswordModal(user: User) {
    const dialogRef = this.dialog.open(PasswordDialogComponent, {
    });

    dialogRef.afterClosed().subscribe(data => {
      if (data) {
        this.usersService.updateGuestPassword(user.id,data).subscribe({
          next: () => {
            // Password updated successfully
            this.loadGuestUsers();
          },
          error: (error) => {
            console.error('Error updating password:', error);
          }
        });
      }
    });
  }

  loadGuestUsers() {
    this.guestsLoading = true;
    this.usersService.getAllGuests()
      .pipe(finalize(() => this.guestsLoading = false))
      .subscribe({
        next: users => {
          this.guestUsers = users;
          this.applyGuestFilters();
        },
        error: error => {
          console.error('Error loading guest users:', error);
        }
      });
  }

  loadAllUsers() {
    this.usersLoading = true;
    this.usersService.getUsers()
      .pipe(finalize(() => this.usersLoading = false))
      .subscribe({
        next: users => {
          this.allUsers = users;
          this.applyUserFilters();
        },
        error: error => {
          console.error('Error loading all users:', error);
        }
      });
  }

  changeRole(user: User, newRole: string) {
    if (newRole === user.roles) {
      return;
    }
    if (user.id === this.currentUserId) {
      alert("You cannot change your own role.");
      this.loadAllUsers(); // revert the <select>'s optimistic binding
      return;
    }
    this.usersService.changeUserRole(user.id, newRole).subscribe({
      next: () => {
        this.loadAllUsers();
        this.loadGuestUsers();
      },
      error: error => {
        console.error('Error changing role:', error);
        this.loadAllUsers(); // revert the <select>'s optimistic binding
      }
    });
  }

  toggleUserStatus(user: User) {
    if (user.is_active) {
      // Désactiver coupe l'accès du compte : friction volontaire (confirmation)
      // avant d'agir, contrairement à l'activation qui n'a rien de destructif.
      const dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: {
          title: 'Deactivate account',
          message: `Deactivate ${user.email}? They will no longer be able to sign in.`,
          confirmLabel: 'Deactivate',
          danger: true,
        },
        width: '420px',
        panelClass: 'confirm-dialog-panel',
      });

      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.usersService.deactivateGuest(user.id).subscribe({
            next: () => {
              this.loadGuestUsers();
              this.loadAllUsers();
            },
            error: error => console.error('Error updating status:', error),
          });
        }
      });
      return;
    }

    this.usersService.activateGuest(user.id).subscribe({
      next: () => {
        this.loadGuestUsers();
        this.loadAllUsers();
      },
      error: error => console.error('Error updating status:', error),
    });
  }

  deleteUser(user: User) {
    if (user.id === this.currentUserId) {
      alert("You cannot delete your own account.");
      return;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Delete user',
        message: `Delete ${user.email}? This cannot be undone.`,
        confirmLabel: 'Delete',
        danger: true,
      },
      width: '420px',
      panelClass: 'confirm-dialog-panel',
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (!confirmed) {
        return;
      }
      this.usersService.deleteGuest(user.id).subscribe({
        next: () => {
          // DELETE isn't covered by successNotificationInterceptor (POST/PUT/
          // PATCH only, cf. success-notification.interceptor.ts) -- shown
          // manually here instead.
          this.successNotificationService.showSuccess('User deleted successfully.');
          this.loadGuestUsers();
          this.loadAllUsers();
        },
        error: error => {
          console.error('Error deleting user:', error);
        }
      });
    });
  }

  assignBot(user: User) {
    const dialogRef = this.dialog.open(BotAssignmentDialogComponent, {
      data: { user },
      width: '600px',
      minHeight: '500px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.usersService.assignBotsToGuest(user.id, result.assigned_bot_ids)
          .subscribe({
            next: () => {
              this.loadGuestUsers();
              this.loadAllUsers();
            },
            error: (error) => {
              console.error('Error assigning bots:', error);
            }
          });
      }
    });
  }
}
