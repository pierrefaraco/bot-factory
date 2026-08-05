import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { UsersService } from '../../services/users.service';
import { User } from '../../models/user.model';
import { BotService } from '../../services/bot.service';
import { Bot } from '../../models/bot.model';
import { UserDialogComponent } from './user-dialog/user-dialog.component';
import { PasswordDialogComponent } from './password-dialog/password-dialog.component';
import { BotAssignmentDialogComponent } from './bot-assignment-dialog/bot-assignment-dialog.component';
import { finalize } from 'rxjs/operators';
import { ArrayComponent } from '../base/array/array.component';
import { LineComponent } from '../base/array/line/line.component';
import { ColumnComponent } from '../base/array/column/column.component';
import { ButtonComponent } from '../base/button/button.component';
import { CustomDropDownMenuComponent } from '../base/custom-dropdown-menu/custom-dropdown-menu.component';

@Component({
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatIconModule,
    MatDialogModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    UserDialogComponent,
    PasswordDialogComponent,
    BotAssignmentDialogComponent,
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
  @ViewChild(ArrayComponent) arrayComponent: ArrayComponent;
  guestUsers: User[] = [];
  currentPage = 1;
  pageSize = 5;
  totalPages = 1;
  activeTab: 'overview' | 'users' | 'settings' = 'overview';

  actionItemList = [
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
      action:  (user) => {this.deleteUser(user.id)}
    }
  ]
  constructor(
    private dialog: MatDialog,
    private usersService: UsersService,
    private botService: BotService
  ) {}

  ngOnInit(): void {
    this.loadGuestUsers();
  }

  get paginatedUsers() {
      // console.log('paginatedUsers')
      let recordss=this.arrayComponent?.paginatedRecords;
      return recordss
  }

  get activeUsersCount(): number {
    return this.guestUsers.filter(user => user.is_active).length;
  }

  get totalAssignedBots(): number {
    return this.guestUsers.reduce((total, user) => {
      return total + (user.assigned_bot_ids?.length || 0);
    }, 0);
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
      console.log(user)
      if (user) {
        console.log(user)
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
      console.log("result",_user)
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
        console.log("data",data)
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
    console.log("1 loadGuestUsers")
    this.usersService.getAllGuests().subscribe(
      users => {
        console.log("2 loadGuestUsers", users)
        this.guestUsers = users;
        this.totalPages = Math.ceil(users.length / this.pageSize);
        const moduloTotalPage = users.length % this.pageSize;
        for (let i = 0; i < this.pageSize - moduloTotalPage; i++) {
        //  this.guestUsers.push(this.createEmptyUser());
        }
      },
      error => {
        console.error('Error loading guest users:', error);
      }
    );
  }

  toggleUserStatus(user: User) {
    if (user.is_active) {
      this.usersService.deactivateGuest(user.id).subscribe(
        () => {
          this.loadGuestUsers();
        },
        error => {
          console.error('Error updating status:', error);
        }
      );
    } else {
      this.usersService.activateGuest(user.id).subscribe(
        () => {
          this.loadGuestUsers();
        },
        error => {
          console.error('Error updating status:', error);
        }
      );
    }
  }

  deleteUser(userId: number) {
    if (confirm('Are you sure you want to delete this user?')) {
      this.usersService.deleteGuest(userId).subscribe(
        () => {
          this.loadGuestUsers();
        },
        error => {
          console.error('Error deleting user:', error);
        }
      );
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  assignBot(user: User) {
    const dialogRef = this.dialog.open(BotAssignmentDialogComponent, {
      data: { user },
      width: '600px',
      minHeight: '500px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        console.log("result",result)
        this.usersService.assignBotsToGuest(user.id, result.assigned_bot_ids)
          .subscribe({
            next: () => {
              this.loadGuestUsers();
            },
            error: (error) => {
              console.error('Error assigning bots:', error);
            }
          });
      }
    });
  }
}