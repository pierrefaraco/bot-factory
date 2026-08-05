import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: '[appLine]',
  standalone: true,
  imports: [ CommonModule,
    FormsModule,],
  templateUrl: './line.component.html',
  styleUrl: './line.component.scss'
})
export class LineComponent {

}
