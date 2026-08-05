import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: '[appColumn]',
  standalone: true,
  imports: [CommonModule,
    FormsModule,],
  templateUrl: './column.component.html',
  styleUrl: './column.component.scss'
})
export class ColumnComponent {

}
