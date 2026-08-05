import { Component, Input, input } from '@angular/core';
import { ButtonComponent } from '../button/button.component';
import { CommonModule } from '@angular/common';


@Component({
  selector: 'app-array',
  standalone: true,
  imports: [CommonModule,
    ButtonComponent
  ],
  templateUrl: './array.component.html',
  styleUrl: './array.component.scss'
})
export class ArrayComponent {
 @Input() columns_names: string[] = [];
 @Input() records: any [] = [];
 @Input() pageSize: number = 0;
 currentPage: number = 1;
 totalPages: number = 0;



 get paginatedRecords() {
  this.totalPages = Math.ceil(this.records.length / this.pageSize);
  const startIndex = (this.currentPage - 1) * this.pageSize;
  // console.log(this.records.slice(startIndex, startIndex + this.pageSize))
  return this.records;
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

}
